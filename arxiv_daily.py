#!/usr/bin/env python3
"""
arXiv Daily Paper Digest — Autonomous version for GitHub Actions.

Fetches recent papers from arXiv, uses DeepSeek API for AI filtering/ranking,
generates Chinese HTML digest, sends via QQ email.

Usage:
  # Normal run (fetch + filter + email)
  python arxiv_daily.py
  
  # Fetch only (output JSON for debugging)
  python arxiv_daily.py --fetch-only

No external dependencies beyond Python 3.8+ stdlib.
"""

import os
import sys
import json
import time
import argparse
import smtplib
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, timedelta, timezone
from html import escape

# ============================================================
# CONFIGURATION
# ============================================================

# DeepSeek API — set via environment variables
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

# QQ Email — set via environment variables
QQ_SMTP_PASSWORD = os.environ.get("QQ_SMTP_PASSWORD", "")
QQ_SENDER = os.environ.get("QQ_SENDER", "2105845780@qq.com")
QQ_RECEIVER = os.environ.get("QQ_RECEIVER", "2105845780@qq.com")

# arXiv config
ARXIV_API = "https://export.arxiv.org/api/query"
ARXIV_NS = {'a': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
RATE_LIMIT = 3.5  # seconds between arXiv requests
CATEGORIES = ["cs.CV", "cs.RO", "cs.AI", "cs.LG", "cs.MA"]
MAX_PER_CATEGORY = 200
LOOKBACK_DAYS = 3  # look back 3 days for weekend coverage

# User's research interests (used in LLM prompt)
RESEARCH_INTERESTS = """
## 用户研究兴趣

### 1. 自动驾驶 (Autonomous Driving)
关键词: end-to-end driving, planning, trajectory prediction, BEV perception, 
occupancy network, imitation learning, diffusion policy, world model
分类: cs.CV, cs.RO, cs.AI

### 2. VLA / 具身智能 (Vision-Language-Action / Embodied AI)
关键词: vision-language-action, vision language model, VLM, embodied, 
manipulation, robotic, RT-2, open-vocabulary, VLA
分类: cs.CV, cs.RO, cs.AI, cs.LG

### 3. 轨迹预测 (Trajectory Prediction)
关键词: trajectory prediction, motion forecasting, path prediction, 
intent estimation, multimodal trajectory, scene-aware trajectory, 
interactive trajectory, pedestrian/vehicle trajectory
分类: cs.CV, cs.RO, cs.AI

### 4. 多智能体行为建模 (Multi-Agent Behavior Modeling)
关键词: multi-agent behavior modeling, multi-agent system, multi-agent interaction, 
cooperative behavior, swarm, collective intelligence, multi-agent RL, 
social navigation, game theory for agents, traffic flow modeling
分类: cs.MA, cs.RO, cs.AI, cs.LG

### 5. CV 新进展 (Computer Vision)
关键词: object detection, segmentation, 3D reconstruction, NeRF, 
3D Gaussian Splatting, video understanding, image/video generation, 
diffusion models, visual grounding, VLMs
分类: cs.CV
"""


# ============================================================
# ARXIV FETCHER
# ============================================================

def fetch_url(url: str, retries: int = 2) -> str:
    """Fetch a URL with rate limiting and retry on 429."""
    headers = {'User-Agent': 'ArxivDaily-Autonomous/1.0 (mailto:2105845780@qq.com)'}
    for attempt in range(retries + 1):
        if attempt > 0:
            time.sleep(RATE_LIMIT)
        time.sleep(RATE_LIMIT if attempt == 0 else 30)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                print(f"  Rate limited (429), waiting 30s before retry {attempt+1}/{retries}...", file=sys.stderr)
                time.sleep(30)
                continue
            raise
        except Exception as e:
            if attempt < retries:
                print(f"  Fetch failed: {e}, retrying {attempt+1}/{retries}...", file=sys.stderr)
                time.sleep(5)
                continue
            raise
    raise RuntimeError(f"Failed to fetch {url} after {retries} retries")


def parse_entry(entry) -> dict | None:
    """Parse an Atom entry into a paper dict."""
    def txt(tag):
        el = entry.find(f'a:{tag}', ARXIV_NS)
        return el.text.strip().replace('\n', ' ') if el is not None and el.text else ''

    def author_list():
        names = []
        for a in entry.findall('a:author', ARXIV_NS):
            n = a.find('a:name', ARXIV_NS)
            if n is not None and n.text:
                names.append(n.text.strip())
        return ', '.join(names)

    arxiv_url = txt('id')
    arxiv_id = arxiv_url.split('/abs/')[-1] if '/abs/' in arxiv_url else arxiv_url.split('/')[-1]
    summary = txt('summary')
    if 'withdrawn' in summary.lower() or 'retracted' in summary.lower():
        return None

    cats = [c.get('term', '') for c in entry.findall('a:category', ARXIV_NS) if c.get('term')]
    return {
        'arxiv_id': arxiv_id,
        'title': txt('title'),
        'authors': author_list(),
        'published': txt('published')[:10],
        'updated': txt('updated')[:10],
        'summary': summary,
        'categories': cats,
        'primary_category': cats[0] if cats else 'unknown',
        'link': f'https://arxiv.org/abs/{arxiv_id}',
        'pdf': f'https://arxiv.org/pdf/{arxiv_id}',
    }


def search_by_category(category: str, max_results: int = 200) -> list[dict]:
    """Fetch most recent papers from a specific arXiv category."""
    url = (f'{ARXIV_API}?search_query=cat:{category}&'
           f'sortBy=submittedDate&sortOrder=descending&max_results={max_results}')
    print(f"  Fetching {category} (max {max_results})...", file=sys.stderr)
    xml_data = fetch_url(url)
    root = ET.fromstring(xml_data)
    papers = []
    for entry in root.findall('a:entry', ARXIV_NS):
        paper = parse_entry(entry)
        if paper is not None:
            papers.append(paper)
    total_el = root.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults')
    total_count = int(total_el.text) if total_el is not None and total_el.text else len(papers)
    print(f"  {category}: got {len(papers)} papers (total available: {total_count})", file=sys.stderr)
    return papers


def filter_by_days(papers: list[dict], days: int) -> list[dict]:
    """Keep only papers published within the last N days."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    result = []
    for p in papers:
        try:
            pub_date = datetime.strptime(p['published'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if pub_date >= cutoff:
                result.append(p)
        except (ValueError, KeyError):
            pass
    return result


def fetch_papers() -> list[dict]:
    """Main fetch function: get papers from all categories, deduplicate, date filter."""
    all_papers = []
    seen_ids = set()
    for cat in CATEGORIES:
        for p in search_by_category(cat, MAX_PER_CATEGORY):
            if p['arxiv_id'] not in seen_ids:
                seen_ids.add(p['arxiv_id'])
                all_papers.append(p)

    papers = filter_by_days(all_papers, LOOKBACK_DAYS)
    if len(papers) < 5:
        print(f"  Only {len(papers)} papers in {LOOKBACK_DAYS} day(s), expanding to 5...", file=sys.stderr)
        papers = filter_by_days(all_papers, 5)

    papers.sort(key=lambda p: p['published'], reverse=True)
    print(f"  Total unique papers after dedup + date filter: {len(papers)}", file=sys.stderr)
    return papers


# ============================================================
# DEEPSEEK API — AI Filtering & Digest Generation
# ============================================================

def call_deepseek(messages, temperature=0.3, max_tokens=4096):
    """Call DeepSeek Chat API with OpenAI-compatible endpoint."""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not set")

    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    payload = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    })

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        print(f"DeepSeek API error ({e.code}): {e.read().decode()}", file=sys.stderr)
        raise
    except Exception as e:
        print(f"DeepSeek API call failed: {e}", file=sys.stderr)
        raise


def build_filter_prompt(papers: list[dict]) -> str:
    """Build the prompt for DeepSeek to filter and rank papers."""
    papers_json = json.dumps(papers, ensure_ascii=False, indent=2)
    today = datetime.now().strftime('%Y-%m-%d')

    return f"""你是一个专业的AI研究助手，负责从arXiv论文列表中筛选出与用户研究兴趣高度相关的论文，并生成中文日报。

今天是 {today}。

## 用户研究兴趣
{RESEARCH_INTERESTS}

## 任务
分析以下 {len(papers)} 篇论文，按以下步骤：

### 步骤1：相关性筛选
对每篇论文评估相关性：
- **强相关**（⭐⭐⭐）：直接命中关键词，或研究内容高度可迁移
- **相关**（⭐⭐）：有启发价值，间接相关
- **弱相关/不相关**（⭐ 或不选）：跳过

### 步骤2：按主题分组
将强相关和相关的论文按以下板块分组：
1. 🚗 **自动驾驶 / 轨迹预测** — end-to-end driving, planning, trajectory prediction, BEV, occupancy, world model
2. 🤖 **VLA / 具身智能** — vision-language-action, robotic manipulation, VLM for robotics
3. 👥 **多智能体行为建模** — multi-agent interaction, cooperative behavior, swarm, social navigation
4. 👁️ **CV 新进展** — 检测/分割/3D重建/NeRF/Gaussian Splatting/视频生成等
5. 📌 **扩展阅读** — 弱相关但有启发价值的论文

### 步骤3：生成日报

输出格式必须是 **纯HTML表格**，符合以下模板（不要Markdown，不要```html代码块，直接输出纯HTML）：

```html
<h3>📄 arXiv 论文日报 — {today}</h3>
<p>共筛选 <strong>X</strong> 篇，来自 {', '.join(CATEGORIES)}</p>
<hr>

<h4>🚗 自动驾驶 / 轨迹预测</h4>
<table border="0" cellpadding="8" cellspacing="0" width="100%" style="font-family: Arial, sans-serif;">
<tr style="background:#f0f0f0;font-weight:bold;"><td width="60%">论文</td><td width="30%">亮点</td><td width="10%">评级</td></tr>
...（每篇一行）
</table>

... 其他板块同理
```

### 重要要求：
- 每篇论文给出一句话中文亮点点评（为什么值得看，不要长摘要）
- 论文标题保留英文原文并链接到 arxiv.org/abs/ID
- 作者只保留前3个加"et al."
- 每个板块如果只有0篇则跳过不显示
- 严格按⭐⭐⭐、⭐⭐、⭐三级
- 整体精选 **18-22篇**，宁缺毋滥

### 论文列表：
{papers_json}
"""


def build_plaintext_digest(html_digest: str) -> str:
    """Strip HTML to plain text for email fallback."""
    import re
    text = re.sub(r'<[^>]+>', ' ', html_digest)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_digest(papers: list[dict]) -> str:
    """Call DeepSeek to generate the HTML digest."""
    print("  Calling DeepSeek API for filtering & digest generation...", file=sys.stderr)
    prompt = build_filter_prompt(papers)
    messages = [
        {"role": "system", "content": "你是一个专业的AI研究助手，精通自动驾驶、VLA、CV等领域。请直接输出纯HTML，不要用Markdown代码块包裹。"},
        {"role": "user", "content": prompt},
    ]
    html_digest = call_deepseek(messages, temperature=0.3, max_tokens=12288)
    return html_digest


# ============================================================
# EMAIL SENDER
# ============================================================

def build_email_html(digest_html: str) -> str:
    """Wrap the digest HTML in a complete email template."""
    today = datetime.now().strftime('%Y-%m-%d')
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>arXiv Paper Digest {today}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
       background: #f5f5f5; margin: 0; padding: 20px; color: #333; }}
.container {{ max-width: 720px; margin: 0 auto; background: white; border-radius: 12px; 
              padding: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
h3 {{ color: #1a1a1a; margin-top: 0; }}
h4 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 6px; margin-top: 28px; }}
table {{ border-collapse: collapse; }}
td {{ padding: 10px 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
tr:hover {{ background: #f8f9fa; }}
a {{ color: #2980b9; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.stars {{ color: #f39c12; letter-spacing: 1px; }}
.footer {{ margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; 
          font-size: 12px; color: #999; text-align: center; }}
hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 16px 0; }}
p {{ line-height: 1.6; }}
</style>
</head>
<body>
<div class="container">
{digest_html}
<div class="footer">
  本日报由 arXiv Daily 自动生成 · 使用 DeepSeek API 进行AI筛选<br>
  每天北京时间 20:00 推送 · <a href="https://github.com/Mar-Ding/arxiv-daily">GitHub</a>
</div>
</div>
</body>
</html>"""


def send_email(html_body: str):
    """Send HTML email via QQ SMTP."""
    if not QQ_SMTP_PASSWORD:
        raise ValueError("QQ_SMTP_PASSWORD not set")

    today = datetime.now().strftime('%Y-%m-%d')
    subject = f"arXiv 论文日报 — {today}"

    msg = MIMEMultipart('alternative')
    msg['From'] = QQ_SENDER
    msg['To'] = QQ_RECEIVER
    msg['Subject'] = Header(subject, 'utf-8')

    # Plain text fallback
    plain_text = build_plaintext_digest(html_body)
    text_part = MIMEText(plain_text, 'plain', 'utf-8')
    html_part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(text_part)
    msg.attach(html_part)

    SMTP_HOST = "smtp.qq.com"
    SMTP_PORT = 465

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(QQ_SENDER, QQ_SMTP_PASSWORD)
        server.sendmail(QQ_SENDER, [QQ_RECEIVER], msg.as_string())

    print(f"Email sent to {QQ_RECEIVER}: {subject}", file=sys.stderr)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='arXiv Daily Paper Digest')
    parser.add_argument('--fetch-only', action='store_true', help='Fetch papers and output JSON, no AI/email')
    parser.add_argument('--output', help='Save digest HTML to file instead of sending email')
    parser.add_argument('--debug-html', action='store_true', help='Print generated HTML to stdout')
    args = parser.parse_args()

    # Validate credentials
    if not QQ_SMTP_PASSWORD and not args.fetch_only and not args.output:
        print("ERROR: QQ_SMTP_PASSWORD environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Step 1: Fetch papers
    print("Step 1/3: Fetching papers from arXiv...", file=sys.stderr)
    try:
        papers = fetch_papers()
    except Exception as e:
        print(f"ERROR fetching papers: {e}", file=sys.stderr)
        sys.exit(1)

    if not papers:
        print("No papers found. Exiting.", file=sys.stderr)
        sys.exit(0)

    if args.fetch_only:
        result = {
            'fetched_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'total': len(papers),
            'papers': papers,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Step 2: AI filtering & digest generation
    print(f"Step 2/3: AI filtering {len(papers)} papers via DeepSeek...", file=sys.stderr)
    try:
        digest_html = generate_digest(papers)
    except Exception as e:
        print(f"ERROR generating digest: {e}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Build email and send/save
    print("Step 3/3: Building and delivering email...", file=sys.stderr)
    full_html = build_email_html(digest_html)

    if args.debug_html:
        print(full_html)
        return

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"Digest saved to {args.output}", file=sys.stderr)
    else:
        send_email(full_html)

    print("Done!", file=sys.stderr)


if __name__ == '__main__':
    main()
