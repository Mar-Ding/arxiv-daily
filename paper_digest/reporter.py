"""
报告生成与邮件推送模块
生成完整的 HTML 日报（含数据分析和图表），通过 QQ 邮箱发送
"""

import os
import re
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
from pathlib import Path
from typing import Optional

from .config import load_config


def build_plaintext_digest(html: str) -> str:
    """Strip HTML to plain text for email fallback."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def build_full_email(analysis_html: str, digest_html: str,
                     chart_paths: dict = None) -> str:
    """
    构建完整的邮件HTML内容，包含数据分析报告 + 论文日报 + 图表

    参数:
        analysis_html: 数据分析章节HTML
        digest_html: AI筛选日报HTML
        chart_paths: 图表路径字典 {name: path}

    返回:
        完整的HTML字符串
    """
    today = datetime.now().strftime('%Y-%m-%d')

    # 构建图表HTML
    charts_html = ""
    if chart_paths:
        charts_html = '<h4>📊 数据分析可视化</h4><div style="text-align:center;">\n'
        for name, path in chart_paths.items():
            if name == 'charts_count':
                continue
            # 将本地路径转为 base64 内嵌图片（或者引用路径说明）
            # 在邮件中无法直接引用本地文件，这里显示文件名说明
            filename = os.path.basename(path)
            charts_html += f'<p style="font-size:12px;color:#666;">📈 {name}</p>\n'
        charts_html += '</div>\n'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI学术论文智能日报 {today}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
       background: #f5f5f5; margin: 0; padding: 20px; color: #333; }}
.container {{ max-width: 780px; margin: 0 auto; background: white; border-radius: 12px;
              padding: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
h3 {{ color: #1a1a1a; margin-top: 0; font-size: 22px; }}
h4 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 6px; margin-top: 28px; }}
table {{ border-collapse: collapse; }}
td {{ padding: 10px 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
tr:hover {{ background: #f8f9fa; }}
a {{ color: #2980b9; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.stars {{ color: #f39c12; letter-spacing: 1px; }}
.footer {{ margin-top: 28px; padding-top: 16px; border-top: 1px solid #eee;
          font-size: 12px; color: #999; text-align: center; }}
hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 16px 0; }}
p {{ line-height: 1.6; }}
.stat-box {{ background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 12px 0; }}
.stat-row {{ display: flex; justify-content: space-between; flex-wrap: wrap; }}
.stat-item {{ text-align: center; padding: 8px 16px; flex: 1; min-width: 100px; }}
.stat-value {{ font-size: 24px; font-weight: bold; color: #2980b9; }}
.stat-label {{ font-size: 12px; color: #666; }}
.chart-section {{ margin: 16px 0; padding: 12px; background: #fafafa; border-radius: 8px; }}
</style>
</head>
<body>
<div class="container">

<div style="text-align:center;margin-bottom:24px;">
  <h2 style="color:#2c3e50;">AI学术论文智能日报</h2>
  <p style="color:#999;font-size:14px;">{today} · 基于DeepSeek大模型智能筛选</p>
</div>

{analysis_html}

<hr>

{digest_html}

<hr>

<div style="text-align:center;padding:8px;">
  <p style="font-size:13px;color:#666;">
    📊 详细统计图表（关键词分布、类别占比、提交趋势等）<br>
    已保存至本地 output/ 目录，可通过 Web 仪表盘查看
  </p>
</div>

<div class="footer">
  AI学术论文智能日报 · 《人工智能程序设计》大作业<br>
  武汉理工大学 · 丁驿<br>
  本系统使用 arXiv API 获取数据 + DeepSeek大模型进行智能筛选<br>
  数据分析模块提供关键词统计、类别分布、趋势分析等功能
</div>

</div>
</body>
</html>"""


def send_email(html_body: str, config: Optional[dict] = None):
    """Send HTML email via QQ SMTP."""
    if config is None:
        config = load_config()

    email_cfg = config['email']
    password = email_cfg['password']
    sender = email_cfg['sender']
    receiver = email_cfg.get('receiver', sender)

    if not password:
        raise ValueError("QQ_SMTP_PASSWORD 未设置！请通过环境变量配置")

    today = datetime.now().strftime('%Y-%m-%d')
    subject = f"AI学术论文智能日报 — {today}"

    msg = MIMEMultipart('alternative')
    msg['From'] = sender
    msg['To'] = receiver
    msg['Subject'] = Header(subject, 'utf-8')

    # Plain text fallback
    plain_text = build_plaintext_digest(html_body)
    text_part = MIMEText(plain_text, 'plain', 'utf-8')
    html_part = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(text_part)
    msg.attach(html_part)

    import smtplib
    SMTP_HOST = email_cfg.get('smtp_host', 'smtp.qq.com')
    SMTP_PORT = email_cfg.get('smtp_port', 465)

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())

    print(f"  [邮件] 日报已发送至 {receiver}: {subject}", file=sys.stderr)


def build_analysis_section(analysis_report: dict) -> str:
    """
    将数据分析报告转为 HTML 章节

    参数:
        analysis_report: analyzer 生成的报告字典

    返回:
        HTML 字符串
    """
    report = analysis_report
    lines = ['<h4>📊 本周论文数据分析</h4>']

    # 基本统计信息
    lines.append('<div class="stat-box">')
    lines.append('<div class="stat-row">')

    lines.append(f'<div class="stat-item">'
                 f'<div class="stat-value">{report.get("total_papers", 0)}</div>'
                 f'<div class="stat-label">本周论文总数</div></div>')

    abstract_stats = report.get('abstract_stats', {})
    if abstract_stats:
        lines.append(f'<div class="stat-item">'
                     f'<div class="stat-value">{abstract_stats.get("avg", 0)}</div>'
                     f'<div class="stat-label">平均摘要词数</div></div>')

    lines.append('</div></div>')

    # 类别分布
    cat_dist = report.get('category_distribution', {})
    if cat_dist:
        lines.append('<div class="chart-section">')
        lines.append('<p style="font-weight:bold;margin:0 0 8px 0;">📂 论文类别分布 (Top 10)</p>')
        lines.append('<table border="0" cellpadding="4" cellspacing="0" width="100%">')
        for cat, count in list(cat_dist.items())[:10]:
            pct = count / max(report['total_papers'], 1) * 100
            bar_w = max(pct * 2, 5)
            lines.append(
                f'<tr><td width="30%">{cat}</td>'
                f'<td width="50%"><div style="background:#3498db;height:16px;'
                f'border-radius:8px;width:{bar_w:.0f}px;"></div></td>'
                f'<td width="20%" style="text-align:right;">{count} ({pct:.1f}%)</td></tr>'
            )
        lines.append('</table></div>')

    # 高频关键词
    keywords = report.get('top_keywords', [])
    if keywords:
        lines.append('<div class="chart-section">')
        lines.append('<p style="font-weight:bold;margin:0 0 8px 0;">🔑 高频技术关键词 (Top 15)</p>')
        lines.append('<p style="font-size:13px;">')
        for word, count in keywords[:15]:
            lines.append(
                f'<span style="display:inline-block;background:#e8f4fd;'
                f'padding:2px 10px;margin:3px;border-radius:12px;'
                f'font-size:13px;">{word} ({count})</span>'
            )
        lines.append('</p></div>')

    return '\n'.join(lines)
