# AI学术论文智能日报系统

**AI Academic Paper Intelligent Daily Digest System**

基于 DeepSeek 大模型与数据分析的 arXiv 论文智能筛选与推送平台。

> 《人工智能程序设计》课程大作业 — 自选题目
> 武汉理工大学 2025-2026-2 学年 · 丁驿

---

## 📋 目录

- [项目简介](#项目简介)
- [系统架构](#系统架构)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [大作业覆盖说明](#大作业覆盖说明)
- [许可证](#许可证)

---

## 项目简介

本系统自动从 arXiv API 抓取计算机视觉、机器人学、人工智能等方向的最新论文，经过 **数据分析与可视化** 以及 **DeepSeek 大模型智能筛选** 后，生成精美 HTML 日报并通过 QQ 邮箱推送，同时提供 Web 仪表盘供浏览和搜索。

### 核心流程

```
arXiv API 抓取 → SQLite 持久化 → 数据分析 → 可视化图表 → 
DeepSeek AI 筛选 → HTML 日报生成 → QQ 邮件推送 / Web 仪表盘
```

---

## 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                      CLI (paper_digest/cli.py)           │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│ 数据抓取  │ 数据分析  │ 可视化   │ AI筛选   │ 报告推送      │
│ fetcher  │ analyzer │visualizer│ filter   │ reporter     │
│          │          │          │   ↓      │   ↓          │
│ arXiv API│ 关键词   │matplotlib│DeepSeek  │ QQ邮箱/Flask  │
│ XML解析  │ 统计描述  │ 4类图表  │ 相关度评估│ Web仪表盘     │
├──────────┴──────────┴──────────┴──────────┴──────────────┤
│                   数据库 (SQLite)                         │
│          papers / digests / keyword_stats                │
└──────────────────────────────────────────────────────────┘
```

---

## 功能特性

### 📡 数据抓取
- 从 arXiv API 抓取 5 个分类（cs.CV, cs.RO, cs.AI, cs.LG, cs.MA）的最新论文
- 自动去重、日期过滤、请求限流与断线重试

### 📊 数据分析
- **高频关键词提取**：基于 AI 领域术语库的统计
- **类别分布分析**：论文研究领域占比统计
- **提交量趋势**：每日论文数量变化
- **作者活跃度分析**：高频作者统计
- **摘要长度分布**：论文摘要字数统计
- **跨类别关联分析**：多类别论文的共现关系

### 📈 数据可视化
- 论文类别分布饼图
- 高频关键词水平柱状图
- 每日提交量趋势折线图
- 跨类别关联热力图
- 摘要长度分布直方图（独立方法）

### 🤖 AI 智能筛选
- 调用 DeepSeek API 对论文进行相关度评估（⭐⭐⭐/⭐⭐/⭐三级）
- 按研究方向自动分组（自动驾驶、VLA/具身智能、多智能体、CV新进展等）
- 生成中文亮点点评，保留英文标题和 arXiv 链接
- 精选 8-12 篇高质量论文，宁缺毋滥

### 📬 多渠道推送
- **QQ 邮件**：精美 HTML 日报，含数据分析章节
- **本地 HTML**：保存到本地文件，浏览器可直接打开
- **Web 仪表盘**：Flask 页面，支持浏览、搜索、查看历史

### 🗄️ 数据持久化
- SQLite 三表结构（papers, digests, keyword_stats）
- 增量存储，避免重复抓取
- 支持历史数据回溯和统计

---

## 快速开始

### 环境要求

- Python 3.8+
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）
- QQ 邮箱 SMTP 授权码（可选，用于邮件推送）

### 安装

```bash
# 克隆仓库
git clone https://github.com/Mar-Ding/arxiv-daily.git
cd arxiv-daily

# 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 设置环境变量（必填）
export DEEPSEEK_API_KEY="sk-你的key"

# 设置邮箱（如需邮件推送）
export QQ_SMTP_PASSWORD="你的QQ邮箱SMTP授权码"
```

或在 `config.yaml` 中修改其他参数（分类、速率限制等）。

### 运行完整流程

```bash
# 完整流程：抓取 → 分析 → 可视化 → AI筛选 → 邮件推送
python -m paper_digest.cli digest

# 仅保存HTML，不发送邮件
python -m paper_digest.cli digest --no-email
```

---

## 使用指南

### 命令行

```bash
# 完整流程
python -m paper_digest.cli digest              # 抓取→分析→可视化→AI筛选→推送
python -m paper_digest.cli digest --no-email    # 同上，但不发送邮件

# 分步操作
python -m paper_digest.cli fetch                # 仅抓取论文
python -m paper_digest.cli analyze              # 仅数据分析
python -m paper_digest.cli analyze --use-db     # 从已有数据库分析
python -m paper_digest.cli visualize            # 仅生成可视化图表
python -m paper_digest.cli visualize --use-db   # 从已有数据库生成图表

# Web 仪表盘
python -m paper_digest.cli web                  # 启动HTTP服务
python -m paper_digest.cli web --port 8080      # 指定端口
```

### 配置文件

`config.yaml` 中可自定义：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `arxiv.categories` | 抓取的 arXiv 分类 | `[cs.CV, cs.RO, cs.AI, cs.LG, cs.MA]` |
| `arxiv.rate_limit` | API 请求间隔(秒) | `8` |
| `arxiv.lookback_days` | 回溯天数 | `3` |
| `llm.deepseek.model` | DeepSeek 模型 | `deepseek-chat` |
| `email.sender` | 发件邮箱 | `2105845780@qq.com` |

### 环境变量

| 变量 | 说明 | 必需 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | ✅ 是 |
| `DEEPSEEK_BASE_URL` | API 地址（默认 `https://api.deepseek.com/v1`） | ❌ |
| `DEEPSEEK_MODEL` | 模型名（默认 `deepseek-chat`） | ❌ |
| `QQ_SMTP_PASSWORD` | QQ邮箱SMTP授权码 | ⚠️ 邮件推送时需要 |
| `QQ_SENDER` | 发件邮箱（默认 `2105845780@qq.com`） | ❌ |
| `QQ_RECEIVER` | 收件邮箱（默认同发件人） | ❌ |

### 输出文件

运行后生成的文件位于 `output/` 目录：

```
output/
├── digest_YYYY-MM-DD.html    # HTML日报
├── category_distribution.png  # 类别分布饼图
├── keyword_frequency.png      # 关键词柱状图
├── submission_trend.png       # 提交趋势折线图
└── cross_category.png         # 跨类别热力图
```

---

## 项目结构

```
├── paper_digest/              # 核心模块包
│   ├── __init__.py
│   ├── config.py              # 配置管理（YAML + 环境变量）
│   ├── fetcher.py             # arXiv API 数据抓取
│   ├── database.py            # SQLite 持久化
│   ├── analyzer.py            # 数据分析（关键词/统计/趋势）
│   ├── visualizer.py          # matplotlib 可视化
│   ├── llm_engine.py          # DeepSeek API 调用
│   ├── filter.py              # AI 筛选与日报生成
│   ├── reporter.py            # HTML 报告与邮件推送
│   └── cli.py                 # 命令行入口
├── webui/                     # Web 仪表盘
│   ├── app.py                 # Flask 应用
│   └── templates/             # HTML 模板
│       ├── index.html         # 数据总览
│       ├── charts.html        # 可视化图表
│       ├── papers.html        # 论文列表
│       ├── digests.html       # 日报历史
│       └── search.html        # 论文搜索
├── data/                      # SQLite 数据库（自动生成）
├── output/                    # 输出文件（自动生成）
├── config.yaml                # 用户配置文件
├── requirements.txt           # 依赖清单
└── README.md
```

---

## 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.8+ | 主开发语言 |
| urllib / xml.etree | arXiv API 数据抓取与 XML 解析 |
| SQLite3 | 本地持久化存储 |
| matplotlib | 数据可视化（饼图/柱状图/折线图/热力图） |
| DeepSeek API | 大模型智能论文筛选与摘要生成 |
| Flask | Web 仪表盘后端 |
| smtplib / email | QQ 邮箱 SMTP 邮件推送 |
| PyYAML | 配置文件解析 |

---

## 大作业覆盖说明

本系统对应《人工智能程序设计》课程要求的以下方面：

| 课程要求 | 对应实现 |
|----------|---------|
| **大模型 API 调用** | 调用 DeepSeek API 实现论文相关度评估、自动分组与中文亮点生成 |
| **数据分析** | 关键词频次统计、类别分布分析、提交量趋势、作者活跃度、摘要长度分布 |
| **数据可视化** | 4 类 matplotlib 统计图表 |
| **软件开发** | 模块化架构、命令行接口、Web 界面、配置文件、异常处理、日志输出 |
| **结果准确性分析** | LLM 评估结果展示（⭐评级）、数据来源（arXiv API）可信度说明 |
| **报告材料** | 系统自动生成带数据分析章节的 HTML 日报，可作为报告插图 |

---

## 许可证

MIT License
