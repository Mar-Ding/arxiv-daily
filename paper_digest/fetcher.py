"""
arXiv 数据抓取模块
从 arXiv API 获取论文数据，解析 XML，支持断线重试
"""

import time
import sys
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

from .config import load_config

ARXIV_NS = {
    'a': 'http://www.w3.org/2005/Atom',
    'arxiv': 'http://arxiv.org/schemas/atom',
}


def fetch_url(url: str, rate_limit: float = 8, retries: int = 3,
              user_agent: str = None) -> str:
    """Fetch a URL with rate limiting and retry on errors."""
    if user_agent is None:
        user_agent = "ArxivDaily/2.0 (mailto:2105845780@qq.com)"
    headers = {'User-Agent': user_agent}

    for attempt in range(retries + 1):
        if attempt > 0:
            time.sleep(rate_limit)
        time.sleep(rate_limit if attempt == 0 else 30)
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                print(f"  Rate limited (429), waiting 30s before retry "
                      f"{attempt+1}/{retries}...", file=sys.stderr)
                time.sleep(30)
                continue
            raise
        except Exception as e:
            if attempt < retries:
                print(f"  Fetch failed: {e}, retrying {attempt+1}/{retries}...",
                      file=sys.stderr)
                time.sleep(5)
                continue
            raise
    raise RuntimeError(f"Failed to fetch {url} after {retries} retries")


def parse_entry(entry) -> dict | None:
    """Parse an Atom XML entry into a paper dict."""
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
    # 过滤撤稿论文
    if 'withdrawn' in summary.lower() or 'retracted' in summary.lower():
        return None

    cats = [c.get('term', '') for c in entry.findall('a:category', ARXIV_NS) if c.get('term')]
    title = txt('title')
    # 清理多余空格
    title = ' '.join(title.split())

    return {
        'arxiv_id': arxiv_id,
        'title': title,
        'authors': author_list(),
        'published': txt('published')[:10],
        'updated': txt('updated')[:10],
        'summary': ' '.join(summary.split()),
        'categories': cats,
        'primary_category': cats[0] if cats else 'unknown',
        'link': f'https://arxiv.org/abs/{arxiv_id}',
        'pdf': f'https://arxiv.org/pdf/{arxiv_id}',
    }


def search_by_category(category: str, max_results: int = 200,
                       api_url: str = "https://export.arxiv.org/api/query",
                       rate_limit: float = 8,
                       user_agent: str = None) -> list[dict]:
    """Fetch most recent papers from a specific arXiv category."""
    url = (f'{api_url}?search_query=cat:{category}&'
           f'sortBy=submittedDate&sortOrder=descending&max_results={max_results}')
    print(f"  Fetching {category} (max {max_results})...", file=sys.stderr)
    xml_data = fetch_url(url, rate_limit, user_agent=user_agent)
    root = ET.fromstring(xml_data)
    papers = []
    for entry in root.findall('a:entry', ARXIV_NS):
        paper = parse_entry(entry)
        if paper is not None:
            papers.append(paper)
    total_el = root.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults')
    total_count = int(total_el.text) if total_el is not None and total_el.text else len(papers)
    print(f"  {category}: got {len(papers)} papers (total available: {total_count})",
          file=sys.stderr)
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


def fetch_papers(config: dict = None) -> list[dict]:
    """
    主抓取函数：从所有分类获取论文，去重，按日期过滤

    返回论文列表，每篇包含: arxiv_id, title, authors, published, updated,
    summary, categories, primary_category, link, pdf
    """
    if config is None:
        config = load_config()

    arxiv_cfg = config['arxiv']
    categories = arxiv_cfg['categories']
    max_per = arxiv_cfg['max_per_category']
    lookback = arxiv_cfg['lookback_days']
    api_url = arxiv_cfg['api_url']
    rate_limit = arxiv_cfg['rate_limit']
    user_agent = arxiv_cfg.get('user_agent')

    all_papers = []
    seen_ids = set()

    for cat in categories:
        try:
            papers = search_by_category(cat, max_per, api_url, rate_limit, user_agent)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {cat}: {e}, skipping", file=sys.stderr)
            continue
        for p in papers:
            if p['arxiv_id'] not in seen_ids:
                seen_ids.add(p['arxiv_id'])
                all_papers.append(p)

    papers = filter_by_days(all_papers, lookback)
    if len(papers) < 5:
        print(f"  Only {len(papers)} papers in {lookback} day(s), expanding to 5...",
              file=sys.stderr)
        papers = filter_by_days(all_papers, 5)

    papers.sort(key=lambda p: p['published'], reverse=True)
    print(f"  Total unique papers after dedup + date filter: {len(papers)}",
          file=sys.stderr)
    return papers
