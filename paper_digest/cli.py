"""
CLI 命令行入口
支持多种运行模式：完整流程、仅抓取、仅分析、仅可视化、Web仪表盘
"""

import argparse
import json
import sys
import os
from datetime import datetime

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paper_digest.config import load_config
from paper_digest.fetcher import fetch_papers
from paper_digest.database import PaperDatabase
from paper_digest.analyzer import PaperAnalyzer
from paper_digest.visualizer import PaperVisualizer
from paper_digest.filter import PaperFilter
from paper_digest.reporter import build_full_email, build_analysis_section, send_email


def cmd_fetch(args):
    """仅抓取论文，输出JSON"""
    config = load_config()
    print("📡 正在从 arXiv API 抓取论文...", file=sys.stderr)
    papers = fetch_papers(config)
    result = {
        'fetched_at': datetime.now().isoformat(),
        'total': len(papers),
        'papers': papers,
    }
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"已保存到 {args.output}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_analyze(args):
    """仅分析已抓取的数据"""
    config = load_config()
    db = PaperDatabase()

    if args.use_db:
        print("📊 从数据库读取论文进行分析...")
        papers = db.get_recent_papers(days=args.days)
    else:
        print(f"📡 重新抓取近{args.days}天的论文...")
        papers = fetch_papers(config)

    if not papers:
        print("❌ 没有找到论文数据")
        return

    analyzer = PaperAnalyzer(config)
    report = analyzer.generate_full_report(papers)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"📊 数据分析报告")
        print(f"{'='*50}")
        print(f"论文总数: {report['total_papers']}")
        print(f"日期范围: {report.get('date_range', 'N/A')}")
        print(f"\n📂 类别分布:")
        for cat, count in report['category_distribution'].items():
            print(f"  {cat}: {count}")
        print(f"\n🔑 高频关键词 (Top 10):")
        for word, count in report['top_keywords'][:10]:
            print(f"  {word}: {count}")
        print(f"\n📐 摘要统计:")
        stats = report.get('abstract_stats', {})
        if stats:
            print(f"  平均: {stats.get('avg')} 词")
            print(f"  中位数: {stats.get('median')} 词")
            print(f"  范围: {stats.get('min')} ~ {stats.get('max')} 词")


def cmd_visualize(args):
    """生成可视化图表"""
    config = load_config()
    viz = PaperVisualizer()

    # 获取论文数据
    if args.use_db:
        db = PaperDatabase()
        papers = db.get_recent_papers(days=args.days)
    else:
        papers = fetch_papers(config)

    if not papers:
        print("❌ 没有找到论文数据")
        return

    analyzer = PaperAnalyzer(config)
    report = analyzer.generate_full_report(papers)
    charts = viz.generate_all_charts(report)

    print(f"\n📈 可视化完成，共生成 {len(charts)} 张图表:")
    for name, path in charts.items():
        if name != 'charts_count':
            print(f"  {name}: {path}")


def cmd_digest(args):
    """完整流程：抓取 -> 分析 -> 可视化 -> AI筛选 -> 生成日报 -> 发送/保存"""
    config = load_config()
    today = datetime.now().strftime('%Y-%m-%d')

    print(f"\n{'='*50}")
    print(f"📄 AI学术论文智能日报 — {today}")
    print(f"{'='*50}\n")

    # === Step 1: 数据抓取 ===
    print("Step 1/6: 从 arXiv API 抓取最新论文...")
    try:
        papers = fetch_papers(config)
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        sys.exit(1)

    if not papers:
        print("⚠️ 未找到论文，退出")
        sys.exit(0)

    print(f"✅ 共抓取 {len(papers)} 篇论文\n")

    # === Step 2: 数据持久化 ===
    print("Step 2/6: 保存到数据库...")
    db = PaperDatabase()
    new_count = db.save_papers(papers)
    print(f"✅ 新增 {new_count} 篇，数据库总计 {db.get_paper_count()} 篇\n")

    # === Step 3: 数据分析 ===
    print("Step 3/6: 数据分析...")
    analyzer = PaperAnalyzer(config)
    analysis_report = analyzer.generate_full_report(papers)
    # 打印部分结果
    top_keywords = analysis_report['top_keywords'][:10]
    print(f"  热门关键词: {', '.join(f'{w}({c})' for w, c in top_keywords)}")
    print(f"  类别分布: {len(analysis_report['category_distribution'])} 个类别\n")

    # === Step 4: 数据可视化 ===
    print("Step 4/6: 生成可视化图表...")
    viz = PaperVisualizer()
    chart_paths = viz.generate_all_charts(analysis_report)
    print(f"✅ 生成 {len(chart_paths)} 张图表\n")

    # === Step 5: AI筛选 ===
    print("Step 5/6: AI智能筛选...")
    try:
        paper_filter = PaperFilter(config)
        digest_html = paper_filter.generate_digest(papers)
    except Exception as e:
        print(f"⚠️ AI筛选失败: {e}，将使用无AI模式")
        digest_html = f"<p>AI筛选暂时不可用，共获取 {len(papers)} 篇论文。</p>"

    # === Step 6: 生成报告并发送/保存 ===
    print("Step 6/6: 生成报告...")
    analysis_html = build_analysis_section(analysis_report)
    full_html = build_full_email(analysis_html, digest_html, chart_paths)

    if args.no_email:
        output_path = args.output or os.path.join(
            config.get('visualization', {}).get('output_dir', 'output'),
            f"digest_{today}.html"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"✅ HTML 日报已保存: {output_path}")
        print(f"   打开该文件即可在浏览器中查看完整日报")
    else:
        try:
            send_email(full_html, config)
            print(f"✅ 日报已发送至邮箱: {config['email']['receiver']}")
        except Exception as e:
            print(f"⚠️ 邮件发送失败: {e}，已保存到本地")
            output_path = args.output or os.path.join(
                config.get('visualization', {}).get('output_dir', 'output'),
                f"digest_{today}.html"
            )
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_html)
            print(f"✅ HTML 日报已保存: {output_path}")

    # 保存日报记录到数据库
    db.save_digest(today, len(papers), 0, full_html)
    db.close()

    print(f"\n{'='*50}")
    print("✅ 全部完成！")
    print(f"{'='*50}")


def cmd_web(args):
    """启动 Web 仪表盘"""
    from webui.app import start_web
    start_web(host=args.host, port=args.port, debug=args.debug)


def main():
    parser = argparse.ArgumentParser(
        description='AI学术论文智能日报系统 — 《人工智能程序设计》大作业',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 完整流程：抓取+分析+可视化+AI筛选+邮件推送
  python -m paper_digest.cli digest

  # 仅抓取论文
  python -m paper_digest.cli fetch

  # 数据分析和可视化
  python -m paper_digest.cli analyze
  python -m paper_digest.cli visualize

  # 启动Web仪表盘
  python -m paper_digest.cli web
        """
    )
    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # fetch
    p_fetch = subparsers.add_parser('fetch', help='仅抓取论文')
    p_fetch.add_argument('--output', '-o', help='输出JSON文件路径')

    # analyze
    p_analyze = subparsers.add_parser('analyze', help='数据分析')
    p_analyze.add_argument('--use-db', action='store_true', help='从数据库读取而非重新抓取')
    p_analyze.add_argument('--days', type=int, default=3, help='回溯天数 (默认: 3)')
    p_analyze.add_argument('--json', action='store_true', help='以JSON格式输出')

    # visualize
    p_viz = subparsers.add_parser('visualize', help='生成可视化图表')
    p_viz.add_argument('--use-db', action='store_true', help='从数据库读取')
    p_viz.add_argument('--days', type=int, default=3, help='回溯天数')

    # digest (full pipeline)
    p_digest = subparsers.add_parser('digest', help='完整流程：抓取→分析→可视化→AI筛选→推送')
    p_digest.add_argument('--no-email', action='store_true', help='不发送邮件，仅保存HTML到本地')
    p_digest.add_argument('--output', '-o', help='HTML输出路径')

    # web
    p_web = subparsers.add_parser('web', help='启动Web仪表盘')
    p_web.add_argument('--host', default='127.0.0.1', help='监听地址 (默认: 127.0.0.1)')
    p_web.add_argument('--port', type=int, default=5000, help='监听端口 (默认: 5000)')
    p_web.add_argument('--debug', action='store_true', help='调试模式')

    args = parser.parse_args()

    if args.command == 'fetch':
        cmd_fetch(args)
    elif args.command == 'analyze':
        cmd_analyze(args)
    elif args.command == 'visualize':
        cmd_visualize(args)
    elif args.command == 'digest':
        cmd_digest(args)
    elif args.command == 'web':
        cmd_web(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
