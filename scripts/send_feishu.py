#!/usr/bin/env python3
"""Send a compact Feishu notification derived from one daily astronomy Markdown file.

Usage:
    python scripts/send_feishu.py daily/YYYY-MM/YYYY-MM-DD.md

Required environment variable:
    FEISHU_WEBHOOK
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

MAX_TREND_CHARS = 700
MAX_TITLE_CHARS = 180


def parse_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text

    raw = text[4:end]
    body = text[end + 5 :]
    meta: Dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            meta[key] = value
    return meta, body


def extract_section(body: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n?(.*?)(?=^##\s+|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def clean_title(raw: str) -> str:
    title = raw.strip()
    title = re.sub(r"^\d+[.)、]\s*", "", title)
    title = re.sub(r"^\[([^\]]+)\]\([^)]*\)$", r"\1", title)
    title = re.sub(r"\s+", " ", title).strip(" #-\t")
    if len(title) > MAX_TITLE_CHARS:
        title = title[: MAX_TITLE_CHARS - 1].rstrip() + "…"
    return title


def extract_top_papers(body: str, limit: int = 3) -> List[str]:
    section = extract_section(body, "今日最值得关注的论文")
    if not section:
        return []

    titles: List[str] = []
    for line in section.splitlines():
        match = re.match(r"^###\s+(.*)$", line.strip())
        if not match:
            continue
        title = clean_title(match.group(1))
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def compact_markdown_text(text: str, max_chars: int = MAX_TREND_CHARS) -> str:
    if not text:
        return "今日趋势判断未提供。"

    lines: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        lines.append(line)

    result = "\n".join(lines).strip()
    if not result:
        return "今日趋势判断未提供。"
    if len(result) > max_chars:
        result = result[: max_chars - 1].rstrip() + "…"
    return result


def count_selected_papers(body: str) -> int:
    total = 0
    for heading in ("今日最值得关注的论文", "其他精选论文"):
        section = extract_section(body, heading)
        total += len(re.findall(r"^###\s+\d+[.)、]?\s*", section, flags=re.MULTILINE))
    return total


def build_file_url(markdown_path: str) -> str:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    sha = os.environ.get("GITHUB_SHA", "").strip()
    normalized = markdown_path.replace(os.sep, "/").lstrip("./")
    if repo and sha:
        return f"{server}/{repo}/blob/{sha}/{normalized}"
    if repo:
        return f"{server}/{repo}/blob/main/{normalized}"
    return ""


def build_payload(date: str, titles: List[str], trend: str, paper_count: int, url: str) -> dict:
    paper_lines = (
        "\n".join(f"{i}. {title}" for i, title in enumerate(titles, 1))
        if titles
        else "未识别到‘今日最值得关注的论文’条目，请查看全文。"
    )

    summary = (
        f"🔥 **今日最值得关注**\n{paper_lines}\n\n"
        f"📌 **今日趋势**\n{trend}\n\n"
        f"📚 **今日精选：{paper_count if paper_count else '—'} 篇**"
    )

    elements = [{"tag": "div", "text": {"tag": "lark_md", "content": summary}}]
    if url:
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "阅读全文"},
                        "type": "primary",
                        "url": url,
                    }
                ],
            }
        )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": f"🌌 每日天文学与宇宙学简报 · {date}",
                },
            },
            "elements": elements,
        },
    }


def post_json(webhook: str, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Feishu webhook HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Feishu webhook network error: {exc.reason}") from exc

    if not 200 <= status < 300:
        raise RuntimeError(f"Feishu webhook returned HTTP {status}")

    try:
        result = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        result = {}

    for key in ("code", "StatusCode"):
        if key in result and result[key] not in (0, "0"):
            message = result.get("msg") or result.get("StatusMessage") or "unknown error"
            raise RuntimeError(f"Feishu webhook application error: {message}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/send_feishu.py daily/YYYY-MM/YYYY-MM-DD.md", file=sys.stderr)
        return 2

    markdown_path = sys.argv[1]
    path = Path(markdown_path)
    if not path.is_file():
        print(f"Error: Markdown file does not exist: {markdown_path}", file=sys.stderr)
        return 2

    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        print("Error: FEISHU_WEBHOOK is not configured.", file=sys.stderr)
        return 3

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"Error: cannot read UTF-8 Markdown file: {exc}", file=sys.stderr)
        return 2

    meta, body = parse_front_matter(text)
    date = meta.get("date") or path.stem
    titles = extract_top_papers(body, limit=3)
    trend = compact_markdown_text(extract_section(body, "今日趋势判断"))
    paper_count = count_selected_papers(body)
    url = build_file_url(markdown_path)
    payload = build_payload(date, titles, trend, paper_count, url)

    try:
        post_json(webhook, payload)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Feishu notification sent for {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
