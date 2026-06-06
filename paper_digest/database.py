"""
数据库模块 — SQLite 持久化存储历史论文数据
支持增量写入、去重、统计分析查询
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import load_config


class PaperDatabase:
    """论文数据库，管理历史论文的存储与查询"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            config = load_config()
            db_path = config['database']['path']
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()

        # 论文主表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                arxiv_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT,
                published TEXT,
                updated TEXT,
                summary TEXT,
                categories TEXT,
                primary_category TEXT,
                link TEXT,
                pdf TEXT,
                fetched_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # 日报历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS digests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_fetched INTEGER DEFAULT 0,
                total_selected INTEGER DEFAULT 0,
                html_content TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                UNIQUE(date)
            )
        """)

        # 日报-论文关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS digest_papers (
                digest_id INTEGER,
                arxiv_id TEXT,
                relevance TEXT,  -- ⭐⭐⭐/⭐⭐/⭐
                topic_group TEXT, -- 分组
                highlight TEXT,   -- 亮点点评
                FOREIGN KEY (digest_id) REFERENCES digests(id),
                FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
            )
        """)

        # 关键词统计表（供趋势分析使用）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyword_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                date TEXT NOT NULL,
                frequency INTEGER DEFAULT 0,
                UNIQUE(keyword, date)
            )
        """)

        self.conn.commit()

    def save_papers(self, papers: list[dict]) -> int:
        """批量保存论文，返回新增数量"""
        saved = 0
        cursor = self.conn.cursor()
        for p in papers:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO papers
                    (arxiv_id, title, authors, published, updated, summary,
                     categories, primary_category, link, pdf)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p['arxiv_id'], p['title'], p['authors'],
                    p['published'], p['updated'], p['summary'],
                    ','.join(p.get('categories', [])),
                    p.get('primary_category', 'unknown'),
                    p.get('link', ''), p.get('pdf', ''),
                ))
                if cursor.rowcount > 0:
                    saved += 1
            except Exception as e:
                print(f"  DB save error for {p['arxiv_id']}: {e}", file=__import__('sys').stderr)
        self.conn.commit()
        return saved

    def save_digest(self, date: str, total_fetched: int, total_selected: int,
                    html_content: str) -> int:
        """保存日报记录，返回digest_id"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO digests
            (date, total_fetched, total_selected, html_content)
            VALUES (?, ?, ?, ?)
        """, (date, total_fetched, total_selected, html_content))
        self.conn.commit()
        return cursor.lastrowid

    def get_paper_count(self) -> int:
        """返回论文总数"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers")
        return cursor.fetchone()[0]

    def get_statistics(self) -> dict:
        """返回基本统计数据"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers")
        total_papers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT date) FROM digests")
        total_digests = cursor.fetchone()[0]

        cursor.execute("""
            SELECT primary_category, COUNT(*) as cnt
            FROM papers GROUP BY primary_category
            ORDER BY cnt DESC
        """)
        category_dist = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT published, COUNT(*) as cnt
            FROM papers GROUP BY published ORDER BY published
        """)
        daily_trend = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "total_papers": total_papers,
            "total_digests": total_digests,
            "category_distribution": category_dist,
            "daily_trend": daily_trend,
        }

    def search_papers(self, keyword: str, limit: int = 50) -> list[dict]:
        """按关键词搜索论文标题和摘要"""
        cursor = self.conn.cursor()
        like_pattern = f"%{keyword}%"
        cursor.execute("""
            SELECT arxiv_id, title, authors, published, primary_category, link
            FROM papers
            WHERE title LIKE ? OR summary LIKE ?
            ORDER BY published DESC
            LIMIT ?
        """, (like_pattern, like_pattern, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_recent_papers(self, days: int = 7, limit: int = 100) -> list[dict]:
        """获取最近N天的论文"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT arxiv_id, title, authors, published, primary_category, link
            FROM papers
            WHERE published >= date('now', ?)
            ORDER BY published DESC
            LIMIT ?
        """, (f'-{days} days', limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_digest_history(self, limit: int = 30) -> list[dict]:
        """获取日报历史"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, date, total_fetched, total_selected, created_at
            FROM digests
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
