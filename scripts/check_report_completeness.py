#!/usr/bin/env python3
"""Check weekly astronomy-report archive completeness and notify Feishu on gaps.

Scheduled expectation (Asia/Shanghai):
- Daily reports: Monday through Friday of the current week.
- Weekly report: the previous natural week (Monday through Sunday), which
  should already have been produced during the current week.
- Weekly archive consists of both Markdown and BibTeX files.

No Feishu message is sent when everything is complete.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
REPO_URL = "https://github.com/RickWashon/astrophysics-daily-report"


def daily_path(day) -> Path:
    return Path("daily") / day.strftime("%Y-%m") / f"{day.isoformat()}.md"


def weekly_paths(start, end) -> tuple[Path, Path]:
    # Repository convention: weekly/YYYY-MM/ uses the covered week's Monday.
    directory = Path("weekly") / start.strftime("%Y-%m")
    stem = f"{start.isoformat()}_to_{end.isoformat()}"
    return directory / f"{stem}.md", directory / f"{stem}.bib"


def build_payload(now, monday, missing_daily, weekly_start, weekly_end, missing_weekly):
    lines = [
        f"检查时间：{now.strftime('%Y-%m-%d %H:%M')}（Asia/Shanghai）",
        "",
        f"本周日报范围：{monday.isoformat()} — {(monday + timedelta(days=4)).isoformat()}",
    ]

    if missing_daily:
        lines.append("❌ 缺失日报：" + "、".join(d.isoformat() for d in missing_daily))
    else:
        lines.append("✅ 本周工作日日报齐全")

    lines.extend(
        [
            "",
            f"本周应已归档的周报：{weekly_start.isoformat()} — {weekly_end.isoformat()}",
        ]
    )

    if missing_weekly:
        lines.append("❌ 缺失周报文件：")
        lines.extend(f"- {path.as_posix()}" for path in missing_weekly)
    else:
        lines.append("✅ 周报 Markdown 与 BibTeX 齐全")

    lines.extend(
        [
            "",
            "请检查对应 ChatGPT Scheduled Task 的 GitHub 写入步骤。",
        ]
    )

    content = "\n".join(lines)

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "orange",
                "title": {
                    "tag": "plain_text",
                    "content": "⚠️ 天文报告归档有遗漏",
                },
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": content},
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "打开 GitHub 仓库"},
                            "type": "primary",
                            "url": REPO_URL,
                        }
                    ],
                },
            ],
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
    now = datetime.now(TZ)
    today = now.date()

    # Current natural week: Monday -> Sunday.
    monday = today - timedelta(days=today.weekday())

    expected_daily = [monday + timedelta(days=i) for i in range(5)]
    missing_daily = [day for day in expected_daily if not daily_path(day).is_file()]

    # The weekly report expected to already exist this week covers the
    # previous Monday -> Sunday.
    weekly_start = monday - timedelta(days=7)
    weekly_end = monday - timedelta(days=1)
    weekly_md, weekly_bib = weekly_paths(weekly_start, weekly_end)
    missing_weekly = [path for path in (weekly_md, weekly_bib) if not path.is_file()]

    print(f"Asia/Shanghai check time: {now.isoformat(timespec='seconds')}")
    print("Expected daily files:")
    for day in expected_daily:
        path = daily_path(day)
        print(f"  {'OK' if path.is_file() else 'MISSING'} {path.as_posix()}")

    print("Expected weekly files:")
    for path in (weekly_md, weekly_bib):
        print(f"  {'OK' if path.is_file() else 'MISSING'} {path.as_posix()}")

    if not missing_daily and not missing_weekly:
        print("Archive complete. No Feishu notification sent.")
        return 0

    webhook = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not webhook:
        print(
            "Error: report gaps were found but FEISHU_WEBHOOK is not configured.",
            file=sys.stderr,
        )
        return 2

    payload = build_payload(
        now,
        monday,
        missing_daily,
        weekly_start,
        weekly_end,
        missing_weekly,
    )

    try:
        post_json(webhook, payload)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("Missing-report alert sent to Feishu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
