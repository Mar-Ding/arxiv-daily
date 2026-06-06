"""
AI 筛选与摘要生成模块
使用 DeepSeek 大模型对论文进行相关度评估、分组、生成中文日报
"""

import json
import sys
from datetime import datetime

from .config import load_config
from .llm_engine import call_deepseek


class PaperFilter:
    """论文AI筛选器 — 使用DeepSeek评估相关度并生成日报"""

    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.interests = self._build_interests_text()
        ds_cfg = self.config['llm']['deepseek']
        self.api_key = ds_cfg['api_key']
        self.base_url = ds_cfg['base_url']
        self.model = ds_cfg['model']

    def _build_interests_text(self) -> str:
        """将配置中的研究兴趣转为提示词文本"""
        interests = self.config.get('research_interests', {})
        lines = ["## 用户研究兴趣"]
        for topic, info in interests.items():
            keywords = ", ".join(info.get('keywords', []))
            cats = ", ".join(info.get('categories', []))
            lines.append(f"\n### {topic}")
            lines.append(f"关键词: {keywords}")
            lines.append(f"分类: {cats}")
        return "\n".join(lines)

    def generate_digest(self, papers: list[dict]) -> str:
        """
        使用DeepSeek筛选论文并生成HTML日报

        参数:
            papers: 论文列表

        返回:
            HTML日报内容
        """
        papers_json = json.dumps(papers, ensure_ascii=False, indent=2)
        today = datetime.now().strftime('%Y-%m-%d')
        categories = self.config['arxiv']['categories']
        cats_str = ', '.join(categories)

        system_prompt = (
            "你是一个专业的AI研究助手，精通自动驾驶、VLA、CV等领域。"
            "请直接输出纯HTML，不要用Markdown代码块包裹。"
        )

        user_prompt = f"""你是一个专业的AI研究助手，负责从arXiv论文列表中筛选出与用户研究兴趣高度相关的论文，并生成中文日报。

今天是 {today}。

{self.interests}

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

<h3>📄 arXiv 论文日报 — {today}</h3>
<p>共筛选 <strong>X</strong> 篇，来自 {cats_str}</p>
<hr>

<h4>🚗 自动驾驶 / 轨迹预测</h4>
<table border="0" cellpadding="8" cellspacing="0" width="100%" style="font-family: Arial, sans-serif;">
<tr style="background:#f0f0f0;font-weight:bold;"><td width="60%">论文</td><td width="30%">亮点</td><td width="10%">评级</td></tr>
...（每篇一行）
</table>

... 其他板块同理

### 重要要求：
- 每篇论文给出一句话中文亮点点评（为什么值得看，不要长摘要）
- 论文标题保留英文原文并链接到 arxiv.org/abs/ID
- 作者只保留前3个加"et al."
- 每个板块如果只有0篇则跳过不显示
- 严格按⭐⭐⭐、⭐⭐、⭐三级
- 整体精选 **8-12篇**，宁缺毋滥

### 论文列表：
{papers_json}"""

        print(f"  [筛选] 正在调用 DeepSeek ({self.model}) 进行AI筛选...", file=sys.stderr)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        html_digest = call_deepseek(
            messages, temperature=0.3, max_tokens=8192,
            api_key=self.api_key, base_url=self.base_url, model=self.model
        )
        print(f"  [筛选] AI筛选完成，生成日报", file=sys.stderr)
        return html_digest
