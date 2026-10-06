# Astrophysics Daily Report

> GitHub Markdown is the canonical source. This Vault is the local reading and research-organization layer.

## Quick links

- [[daily]] — 每日天文学与宇宙学简报
- [[3day]] — 三日天文文献快报（预留）
- [[weekly]] — 每周天文重磅精选
- [[README]] — 自动化架构、测试与故障排查

## Recommended Obsidian use

- 阅读每天的 `daily/YYYY-MM/YYYY-MM-DD.md`
- 用搜索查论文题目、作者、arXiv 编号和主题
- 在你自己的研究笔记中使用 `[[...]]` 双链引用日报
- 不要把 `.obsidian/` 设备配置提交到 GitHub；每台设备保留自己的界面和插件配置

## Archive layout

```text
daily/YYYY-MM/YYYY-MM-DD.md
3day/
weekly/YYYY-MM/YYYY-MM-DD_to_YYYY-MM-DD.md
weekly/YYYY-MM/YYYY-MM-DD_to_YYYY-MM-DD.bib
bib/
```

正式日报与周报由 ChatGPT Scheduled Task 写入 GitHub；周报仅归档到 `weekly/`，不触发飞书推送。本地 Obsidian 一般通过 Git pull 获取更新。
