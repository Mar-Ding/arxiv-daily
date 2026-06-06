"""
数据分析模块
对论文数据进行统计分析：关键词提取、趋势分析、分类统计
"""

import re
import sys
from collections import Counter
from datetime import datetime
from typing import Optional

# jieba 用于中文关键词分词，但论文数据主要是英文，这里用英文词频
import jieba
import jieba.analyse


class PaperAnalyzer:
    """论文数据分析器"""

    def __init__(self, config: Optional[dict] = None):
        self.config = config

    def extract_keywords(self, papers: list[dict], top_n: int = 30) -> list[tuple]:
        """
        从论文标题和摘要中提取高频关键词（英文为主）
        返回 [(keyword, count), ...]
        """
        # 英文关键词：常见 AI/ML 领域术语
        technical_terms = [
            # 通用
            "transformer", "attention", "diffusion", "reinforcement", "representation",
            "pretraining", "fine-tuning", "zero-shot", "few-shot", "multi-modal",
            "foundation model", "large language model", "LLM", "VLM", "vision-language",
            "self-supervised", "unsupervised", "semi-supervised", "transfer learning",
            "domain adaptation", "generalization", "robustness", "scaling",
            # 自动驾驶/机器人
            "end-to-end", "planning", "control", "navigation", "SLAM",
            "trajectory prediction", "motion planning", "occupancy", "BEV",
            "imitation learning", "world model", "manipulation", "grasping",
            # CV
            "object detection", "semantic segmentation", "instance segmentation",
            "3D reconstruction", "NeRF", "gaussian splatting", "depth estimation",
            "optical flow", "image generation", "video generation", "super resolution",
            # 多智能体
            "multi-agent", "cooperative", "swarm", "communication",
            "game theory", "social navigation",
            # 具身智能
            "embodied", "robotic", "manipulation", "affordance",
        ]

        text = ""
        for p in papers:
            text += (p.get('title', '') + ' ') * 3  # 标题加权
            text += p.get('summary', '') + ' '

        text_lower = text.lower()
        keyword_counts = Counter()

        for term in technical_terms:
            count = text_lower.count(term.lower())
            if count > 0:
                keyword_counts[term] = count

        return keyword_counts.most_common(top_n)

    def category_statistics(self, papers: list[dict]) -> dict:
        """
        统计论文分类分布
        返回: {category: count, ...}
        """
        counter = Counter()
        for p in papers:
            cats = p.get('categories', [])
            if cats:
                counter[cats[0]] += 1
            else:
                counter['unknown'] += 1
        return dict(counter.most_common())

    def daily_submission_trend(self, papers: list[dict]) -> dict:
        """
        统计每日论文提交量趋势
        返回: {date_str: count, ...}
        """
        counter = Counter()
        for p in papers:
            date = p.get('published', '')[:10]
            if date:
                counter[date] += 1
        return dict(sorted(counter.items()))

    def author_analysis(self, papers: list[dict], top_n: int = 20) -> list[tuple]:
        """
        统计分析活跃作者
        返回: [(author_name, count), ...]
        """
        counter = Counter()
        for p in papers:
            authors_str = p.get('authors', '')
            if not authors_str:
                continue
            authors = [a.strip() for a in authors_str.split(',')]
            for author in authors:
                if author:
                    counter[author] += 1
        return counter.most_common(top_n)

    def abstract_length_analysis(self, papers: list[dict]) -> dict:
        """
        摘要长度统计分析
        返回: {min, max, avg, median, distribution: [...]}
        """
        lengths = [len(p.get('summary', '').split()) for p in papers if p.get('summary')]
        if not lengths:
            return {}
        sorted_l = sorted(lengths)
        n = len(sorted_l)
        return {
            "min": min(lengths),
            "max": max(lengths),
            "avg": round(sum(lengths) / n, 1),
            "median": sorted_l[n // 2] if n % 2 else (sorted_l[n // 2 - 1] + sorted_l[n // 2]) / 2,
            "total": n,
        }

    def cross_category_analysis(self, papers: list[dict]) -> list[tuple]:
        """
        跨类别论文分析（一篇论文被分到多个类别）
        返回: [((cat1, cat2), count), ...]
        """
        pairs = Counter()
        for p in papers:
            cats = p.get('categories', [])
            for i in range(len(cats)):
                for j in range(i + 1, len(cats)):
                    pair = tuple(sorted([cats[i], cats[j]]))
                    pairs[pair] += 1
        return pairs.most_common(20)

    def generate_full_report(self, papers: list[dict]) -> dict:
        """生成完整数据分析报告"""
        print("  [分析] 正在生成数据分析报告...", file=sys.stderr)
        report = {
            "total_papers": len(papers),
            "date_range": self._date_range(papers),
            "category_distribution": self.category_statistics(papers),
            "top_keywords": self.extract_keywords(papers, 20),
            "submission_trend": self.daily_submission_trend(papers),
            "top_authors": self.author_analysis(papers, 10),
            "abstract_stats": self.abstract_length_analysis(papers),
            "cross_category": self.cross_category_analysis(papers),
        }
        print(f"  [分析] 完成，共{len(papers)}篇论文，提取{len(report['top_keywords'])}个关键词",
              file=sys.stderr)
        return report

    def _date_range(self, papers: list[dict]) -> str:
        dates = [p.get('published', '')[:10] for p in papers if p.get('published')]
        if dates:
            return f"{min(dates)} ~ {max(dates)}"
        return "N/A"
