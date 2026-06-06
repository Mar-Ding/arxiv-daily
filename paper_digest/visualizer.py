"""
数据可视化模块
使用 matplotlib 生成统计图表：关键词趋势、类别分布、论文提交量变化等
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use('Agg')  # 非交互后端
import matplotlib.pyplot as plt

from .config import load_config


# ============================================================
# 中文字体设置
# ============================================================
def _setup_chinese_font(font_name: str = "SimHei"):
    """尝试设置中文字体，避免图表中文乱码"""
    try:
        plt.rcParams['font.sans-serif'] = [font_name, 'SimHei', 'Microsoft YaHei',
                                            'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass


class PaperVisualizer:
    """论文数据可视化器，生成统计图表"""

    def __init__(self, output_dir: str = None, dpi: int = 150, font: str = "SimHei"):
        config = load_config()
        viz_cfg = config.get('visualization', {})
        self.output_dir = output_dir or viz_cfg.get('output_dir', 'output')
        self.dpi = dpi or viz_cfg.get('dpi', 150)
        _setup_chinese_font(font)
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        print(f"  [可视化] 图表将保存至: {self.output_dir}", file=sys.stderr)

    def plot_category_distribution(self, category_data: dict, top_n: int = 15,
                                   title: str = "论文类别分布",
                                   filename: str = "category_distribution.png"):
        """绘制论文类别分布饼图"""
        if not category_data:
            print("  [可视化] 无类别数据，跳过饼图", file=sys.stderr)
            return None

        sorted_items = sorted(category_data.items(), key=lambda x: x[1], reverse=True)
        top = sorted_items[:top_n]
        others = sum(v for k, v in sorted_items[top_n:])

        labels = [k for k, v in top]
        sizes = [v for k, v in top]
        if others > 0:
            labels.append('其他')
            sizes.append(others)

        colors = plt.cm.Set3([i / len(labels) for i in range(len(labels))])

        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.1f%%',
            colors=colors, startangle=90,
            textprops={'fontsize': 9}
        )
        ax.set_title(title, fontsize=14, pad=20)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"  [可视化] 饼图已保存: {filepath}", file=sys.stderr)
        return filepath

    def plot_keyword_bar(self, keywords: list[tuple], top_n: int = 20,
                         title: str = "高频技术关键词",
                         filename: str = "keyword_frequency.png"):
        """绘制关键词频率柱状图"""
        if not keywords:
            print("  [可视化] 无关键词数据，跳过柱状图", file=sys.stderr)
            return None

        top = keywords[:top_n]
        words = [k for k, v in top][::-1]
        counts = [v for k, v in top][::-1]

        fig, ax = plt.subplots(figsize=(10, max(6, len(words) * 0.35)))
        colors = plt.cm.Blues([0.4 + 0.6 * i / len(counts) for i in range(len(counts))])
        bars = ax.barh(words, counts, color=colors)
        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                    str(count), va='center', fontsize=9)
        ax.set_xlabel('出现次数')
        ax.set_title(title, fontsize=14)
        ax.set_xlim(0, max(counts) * 1.15)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"  [可视化] 关键词柱状图已保存: {filepath}", file=sys.stderr)
        return filepath

    def plot_submission_trend(self, trend_data: dict,
                              title: str = "论文提交量趋势",
                              filename: str = "submission_trend.png"):
        """绘制每日论文提交量趋势图"""
        if not trend_data:
            print("  [可视化] 无趋势数据，跳过折线图", file=sys.stderr)
            return None

        dates = list(trend_data.keys())
        counts = list(trend_data.values())

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(dates, counts, marker='o', linestyle='-', color='#3498db',
                linewidth=1.5, markersize=4)
        ax.fill_between(range(len(dates)), counts, alpha=0.15, color='#3498db')
        ax.set_xlabel('日期')
        ax.set_ylabel('论文数量')
        ax.set_title(title, fontsize=14)

        # 日期标签旋转
        if len(dates) > 10:
            step = max(1, len(dates) // 10)
            tick_positions = list(range(0, len(dates), step))
            ax.set_xticks(tick_positions)
            ax.set_xticklabels([dates[i] for i in tick_positions],
                               rotation=45, ha='right', fontsize=8)
        else:
            ax.set_xticks(range(len(dates)))
            ax.set_xticklabels(dates, rotation=45, ha='right', fontsize=8)
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"  [可视化] 趋势图已保存: {filepath}", file=sys.stderr)
        return filepath

    def plot_cross_category_heatmap(self, cross_data: list[tuple],
                                    title: str = "跨类别论文关联",
                                    filename: str = "cross_category.png"):
        """绘制跨类别关联热力图"""
        if not cross_data:
            print("  [可视化] 无跨类别数据，跳过热力图", file=sys.stderr)
            return None

        top = cross_data[:10]
        all_cats = set()
        for (c1, c2), _ in top:
            all_cats.add(c1)
            all_cats.add(c2)
        all_cats = sorted(all_cats)

        import numpy as np
        matrix = np.zeros((len(all_cats), len(all_cats)))
        cat_to_idx = {c: i for i, c in enumerate(all_cats)}
        for (c1, c2), count in top:
            i, j = cat_to_idx[c1], cat_to_idx[c2]
            matrix[i][j] = count
            matrix[j][i] = count

        fig, ax = plt.subplots(figsize=(8, 7))
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')
        ax.set_xticks(range(len(all_cats)))
        ax.set_yticks(range(len(all_cats)))
        ax.set_xticklabels(all_cats, rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels(all_cats, fontsize=8)
        plt.colorbar(im, ax=ax, label='共现次数')
        ax.set_title(title, fontsize=14)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"  [可视化] 跨类别热力图已保存: {filepath}", file=sys.stderr)
        return filepath

    def plot_abstract_length_histogram(self, papers: list[dict],
                                       title: str = "摘要长度分布",
                                       filename: str = "abstract_length.png"):
        """绘制摘要长度直方图"""
        lengths = [len(p.get('summary', '').split()) for p in papers if p.get('summary')]
        if not lengths:
            print("  [可视化] 无摘要数据，跳过直方图", file=sys.stderr)
            return None

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(lengths, bins=30, color='#2ecc71', alpha=0.7, edgecolor='white')
        ax.axvline(sum(lengths) / len(lengths), color='red', linestyle='--',
                   label=f'平均: {sum(lengths)/len(lengths):.0f}')
        ax.set_xlabel('摘要词数')
        ax.set_ylabel('论文数量')
        ax.set_title(title, fontsize=14)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        print(f"  [可视化] 摘要长度直方图已保存: {filepath}", file=sys.stderr)
        return filepath

    def generate_all_charts(self, analysis_report: dict) -> dict:
        """生成所有图表，返回图表路径字典"""
        print("  [可视化] 正在生成所有统计图表...", file=sys.stderr)
        result = {}

        path = self.plot_category_distribution(
            analysis_report.get('category_distribution', {})
        )
        if path:
            result['category_distribution'] = path

        path = self.plot_keyword_bar(
            analysis_report.get('top_keywords', [])
        )
        if path:
            result['keyword_frequency'] = path

        path = self.plot_submission_trend(
            analysis_report.get('submission_trend', {})
        )
        if path:
            result['submission_trend'] = path

        path = self.plot_cross_category_heatmap(
            analysis_report.get('cross_category', [])
        )
        if path:
            result['cross_category'] = path

        result['charts_count'] = len(result)
        print(f"  [可视化] 共生成 {len(result)} 张图表", file=sys.stderr)
        return result
