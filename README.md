# Astrophysics Daily Report

这是每日天文学与宇宙学科研简报的长期归档仓库。

## 系统架构

```text
ChatGPT Scheduled Task (08:00 Asia/Shanghai)
        │
        └── daily/YYYY-MM/YYYY-MM-DD.md
                    │
                    ├── GitHub = canonical source
                    ├── Obsidian = 阅读 / 搜索 / 双链 / 整理
                    └── push → GitHub Actions → Feishu 摘要通知
```

核心原则：**GitHub Markdown = single source of truth**。飞书只负责每日通知与精简摘要，不保存完整日报。

## 目录结构

```text
daily/               # 每日简报，按自然月归档
3day/                # 预留：三日天文文献快报
weekly/              # 每周天文重磅精选，按覆盖周的周一所属自然月归档
bib/                 # 预留：BibTeX
scripts/send_feishu.py
.github/workflows/daily-feishu.yml
```

每日文件严格使用：

```text
daily/YYYY-MM/YYYY-MM-DD.md
```

周报文件严格使用：

```text
weekly/YYYY-MM/YYYY-MM-DD_to_YYYY-MM-DD.md
weekly/YYYY-MM/YYYY-MM-DD_to_YYYY-MM-DD.bib
```

其中 `weekly/YYYY-MM/` 取该覆盖周**周一**所属的自然月；跨月周不按执行日期改目录。日期和“今天”的判定均使用 `Asia/Shanghai`。

## Scheduled Task → GitHub

ChatGPT 的「每日天文简报」在生成完整日报后：

- 当天文件不存在：创建同日 Markdown，commit 为 `Add daily astronomy brief YYYY-MM-DD`。
- 当天文件已存在：更新同一路径，commit 为 `Update daily astronomy brief YYYY-MM-DD`。
- 不创建 `(1)`、`v2` 等重复文件。
- GitHub 写入失败不得影响日报生成；只有实际写入成功后才能报告保存成功。
- 论文链接必须指向单篇稳定页面，例如 `https://arxiv.org/abs/YYMM.NNNNN`，不得使用 `astro-ph/new`、search、recent 或分类聚合页。

## GitHub Action → Feishu

Workflow 由 push 触发，而不是 cron：

```yaml
on:
  push:
    paths:
      - 'daily/**/*.md'
```

Action 比较 `github.event.before` 与 `github.sha`，只接受 Git 状态 `A`（Added），再检查新增文件是否恰好是 `Asia/Shanghai` 当天的：

```text
daily/YYYY-MM/YYYY-MM-DD.md
```

因此：

- `weekly/**/*.md` 和 `weekly/**/*.bib` 不在 workflow 的监听路径内，**周报不会推送到飞书**。
- 当天日报首次创建：发送一次。
- 同日文件后续修改（`M`）：不发送。
- 补录旧日期日报：不发送。
- 只改 README 等非 daily Markdown：workflow 不触发。

初次 push 或 `github.event.before` 不可用时，workflow 会安全退化到检查 pushed HEAD/root commit，避免 diff base 不存在导致失败。

## Feishu 配置

仓库不保存 webhook 明文。飞书 Incoming Webhook Bot 创建后，只在 GitHub 仓库添加：

```text
Settings → Secrets and variables → Actions → New repository secret
Name: FEISHU_WEBHOOK
```

不要把 webhook 提交到 GitHub，也不要贴进聊天。

`scripts/send_feishu.py` 只使用 Python 标准库，读取 YAML front matter、前三篇重点论文标题和“今日趋势判断”，然后发送精简 interactive card。网络、HTTP 或飞书应用错误会以 non-zero exit code 退出，并且不会打印 webhook。

## Obsidian

推荐方案 A：**直接把本仓库 clone 成一个独立 Obsidian Vault**。这样 GitHub 与 Vault 一一对应，配置最简单，也不会干扰你现有 Vault 的 Git 结构。

方案 B：在现有 Vault 中加入 `Astrophysics Daily Report/` 并同步此仓库。这个方案可能涉及嵌套 Git 仓库、Obsidian Git 插件和既有同步工具之间的冲突，因此不作为第一选择。

Windows 可使用 Git for Windows 或 GitHub Desktop clone 私有仓库后直接用 Obsidian 打开。移动端需要额外处理私有仓库认证；若同时使用 Obsidian Sync，应避免两个同步系统同时修改同一批文件。

## 手动测试

最小日报格式：

```markdown
---
date: YYYY-MM-DD
timezone: Asia/Shanghai
type: daily-astronomy
language: zh-CN
---

# 每日天文学与宇宙学简报：YYYY-MM-DD

## 今日最值得关注的论文

### 1. Test Paper A
### 2. Test Paper B
### 3. Test Paper C

## 今日趋势判断

这是飞书自动推送链路测试。
```

若正式当天文件已存在，应使用临时 branch 测试，不要在 `main` 中额外制造第二份当天日报。

## 防重复验收

| 变化 | 预期 |
|---|---|
| `A daily/<本月>/<今天>.md` | 发送 |
| `M daily/<本月>/<今天>.md` | 不发送 |
| `A daily/<旧月份>/<旧日期>.md` | 不发送 |
| `M README.md` | workflow 不触发 |
| Scheduled Task 正常首次新建当天日报 | 只发送一次 |

## 故障排查

1. **日报生成但 GitHub 没文件**：检查 ChatGPT GitHub connector 是否已授权此私有仓库并具备 push 权限。
2. **Action 没触发**：确认本次 push 实际改变了 `daily/**/*.md`。
3. **Action 正常退出但飞书没消息**：查看 selector 日志；文件必须同时满足 `Added` 与上海时区当天路径。
4. **Secret 检查失败**：检查 `FEISHU_WEBHOOK` repository secret。
5. **脚本返回 HTTP/network error**：检查飞书 webhook 是否仍有效以及机器人安全设置。
6. **修改日报后没有再次通知**：这是预期行为，Modified 文件会被防重复逻辑过滤。

## 后续扩展

三日快报后续可接入 `3day/`。周报已经接入 `weekly/`，仅作为 GitHub/Obsidian 长期归档，不配置飞书推送 workflow。
