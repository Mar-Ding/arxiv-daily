"""
Web 仪表盘 — Flask 应用
展示数据分析结果、图表、论文列表、日报历史
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, render_template, request, send_from_directory

from paper_digest.config import load_config
from paper_digest.database import PaperDatabase
from paper_digest.analyzer import PaperAnalyzer
from paper_digest.visualizer import PaperVisualizer

app = Flask(__name__)
config = load_config()
db = PaperDatabase()


@app.route('/')
def index():
    """数据总览主页"""
    stats = db.get_statistics()
    recent_papers = db.get_recent_papers(days=7, limit=20)
    digests = db.get_digest_history(limit=10)

    # 获取最新生成的图表
    output_dir = config.get('visualization', {}).get('output_dir', 'output')
    charts = {}
    if os.path.exists(output_dir):
        for f in sorted(os.listdir(output_dir)):
            if f.endswith(('.png', '.jpg', '.svg')):
                name = f.replace('.png', '').replace('.jpg', '').replace('.svg', '')
                charts[name] = os.path.join(output_dir, f)

    return render_template(
        'index.html',
        stats={
            'total_papers': stats.get('total_papers', 0),
            'total_digests': stats.get('total_digests', 0),
            'categories': len(stats.get('category_distribution', {})),
        },
        charts=charts,
        recent_papers=recent_papers,
        digests=digests,
    )


@app.route('/charts')
def charts():
    """可视化图表页面"""
    output_dir = config.get('visualization', {}).get('output_dir', 'output')
    charts_list = []
    if os.path.exists(output_dir):
        for f in sorted(os.listdir(output_dir)):
            if f.endswith('.png'):
                charts_list.append({
                    'name': f.replace('.png', '').replace('_', ' ').title(),
                    'filename': f,
                })
    return render_template('charts.html', charts=charts_list)


@app.route('/papers')
def papers():
    """论文列表页面"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    # 简单实现：取最新论文
    papers_list = db.get_recent_papers(days=30, limit=200)
    total = len(papers_list)

    # 分页
    start = (page - 1) * per_page
    end = start + per_page
    page_papers = papers_list[start:end]

    return render_template(
        'papers.html',
        papers=page_papers,
        page=page,
        total=total,
        per_page=per_page,
    )


@app.route('/digests')
def digests():
    """日报历史页面"""
    digest_list = db.get_digest_history(limit=50)
    return render_template('digests.html', digests=digest_list)


@app.route('/digest/<int:digest_id>')
def view_digest(digest_id):
    """查看某期日报"""
    # 从数据库获取日报HTML
    cursor = db.conn.cursor()
    cursor.execute("SELECT html_content FROM digests WHERE id = ?", (digest_id,))
    row = cursor.fetchone()
    if row:
        html_content = row['html_content'] if isinstance(row, dict) else row[0]
        return f'<html><body>{html_content}</body></html>'
    return "日报未找到", 404


@app.route('/search')
def search():
    """论文搜索页面"""
    query = request.args.get('q', '')
    results = None
    if query:
        results = db.search_papers(query, limit=50)
    return render_template('search.html', query=query, results=results)


@app.route('/output/<path:filename>')
def serve_chart(filename):
    """提供图表文件访问"""
    output_dir = config.get('visualization', {}).get('output_dir', 'output')
    return send_from_directory(output_dir, filename)


def start_web(host='127.0.0.1', port=5000, debug=False):
    """启动Web服务器"""
    print(f"\n🌐 Web 仪表盘已启动!")
    print(f"   本地访问: http://{host}:{port}")
    print(f"   按 Ctrl+C 停止\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    start_web()
