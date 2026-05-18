# arXiv Daily Paper Digest

每天北京时间 20:00 自动推送 AI 精选的 arXiv 论文日报到你的 QQ 邮箱。

## 工作流程

1. **Fetch** — 从 arXiv API 拉取 cs.CV, cs.RO, cs.AI, cs.LG, cs.MA 近 3 天的最新论文
2. **AI Filter** — 调用 DeepSeek API 按你的研究兴趣（自动驾驶、VLA/具身智能、轨迹预测、多智能体行为建模、CV）筛选并排序
3. **Deliver** — 生成精美 HTML 日报，通过 QQ 邮箱 SMTP 发送

## 配置

在 GitHub 仓库 Settings > Secrets and variables > Actions 中设置：

| Secret | 说明 | 示例 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxx` |
| `QQ_SMTP_PASSWORD` | QQ邮箱SMTP授权码 | (非QQ密码，需在QQ邮箱设置中生成) |
| `DEEPSEEK_BASE_URL` | (可选) DeepSeek API 地址 | 默认 `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | (可选) 模型名称 | 默认 `deepseek-chat` |
| `QQ_RECEIVER` | (可选) 收件邮箱 | 默认 `2105845780@qq.com` |

## 手动触发

在 GitHub 仓库的 Actions 页面，选择 "arXiv Daily Digest" 工作流，点击 "Run workflow"。
