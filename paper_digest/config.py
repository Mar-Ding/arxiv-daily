"""配置管理模块 — 支持yaml文件 + 环境变量覆盖"""

import os
import yaml
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 默认配置文件路径
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(config_path=None) -> dict:
    """加载配置：先读 yaml，再用环境变量覆盖关键字段"""
    path = config_path or DEFAULT_CONFIG_PATH

    config = {
        # === arXiv API 配置 ===
        "arxiv": {
            "api_url": "https://export.arxiv.org/api/query",
            "rate_limit": 8,               # 请求间隔(秒)
            "categories": ["cs.CV", "cs.RO", "cs.AI", "cs.LG", "cs.MA"],
            "max_per_category": 200,
            "lookback_days": 3,
            "user_agent": "ArxivDaily/2.0 (mailto:2105845780@qq.com)",
        },
        # === LLM 配置 ===
        "llm": {
            "provider": "deepseek",
            "deepseek": {
                "api_key": "",
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
            },
        },
        # === 邮箱配置 ===
        "email": {
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
            "sender": "2105845780@qq.com",
            "password": "",
            "receiver": "2105845780@qq.com",
        },
        # === 数据库配置 ===
        "database": {
            "path": str(PROJECT_ROOT / "data" / "papers.db"),
        },
        # === 可视化配置 ===
        "visualization": {
            "output_dir": str(PROJECT_ROOT / "output"),
            "dpi": 150,
            "font": "SimHei",              # Windows中文字体
        },
        # === 用户研究兴趣 ===
        "research_interests": {
            "自动驾驶": {
                "keywords": ["end-to-end driving", "planning", "trajectory prediction",
                             "BEV perception", "occupancy network", "imitation learning",
                             "diffusion policy", "world model"],
                "categories": ["cs.CV", "cs.RO", "cs.AI"],
            },
            "VLA/具身智能": {
                "keywords": ["vision-language-action", "vision language model", "VLM",
                             "embodied", "manipulation", "robotic", "RT-2",
                             "open-vocabulary", "VLA"],
                "categories": ["cs.CV", "cs.RO", "cs.AI", "cs.LG"],
            },
            "轨迹预测": {
                "keywords": ["trajectory prediction", "motion forecasting",
                             "path prediction", "intent estimation",
                             "multimodal trajectory", "scene-aware trajectory"],
                "categories": ["cs.CV", "cs.RO", "cs.AI"],
            },
            "多智能体行为建模": {
                "keywords": ["multi-agent", "cooperative behavior", "swarm",
                             "collective intelligence", "multi-agent RL",
                             "social navigation", "traffic flow modeling"],
                "categories": ["cs.MA", "cs.RO", "cs.AI", "cs.LG"],
            },
            "CV新进展": {
                "keywords": ["object detection", "segmentation", "3D reconstruction",
                             "NeRF", "3D Gaussian Splatting", "video understanding",
                             "diffusion models", "visual grounding"],
                "categories": ["cs.CV"],
            },
        },
    }

    # 尝试加载 yaml 配置
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
            _deep_merge(config, yaml_config)

    # 环境变量覆盖（优先级最高）
    config["llm"]["deepseek"]["api_key"] = os.environ.get(
        "DEEPSEEK_API_KEY", config["llm"]["deepseek"]["api_key"]
    )
    config["llm"]["deepseek"]["base_url"] = os.environ.get(
        "DEEPSEEK_BASE_URL", config["llm"]["deepseek"]["base_url"]
    )
    config["llm"]["deepseek"]["model"] = os.environ.get(
        "DEEPSEEK_MODEL", config["llm"]["deepseek"]["model"]
    )
    config["email"]["password"] = os.environ.get(
        "QQ_SMTP_PASSWORD", config["email"]["password"]
    )
    config["email"]["sender"] = os.environ.get(
        "QQ_SENDER", config["email"]["sender"]
    )
    config["email"]["receiver"] = os.environ.get(
        "QQ_RECEIVER", config["email"]["receiver"]
    )

    return config


def _deep_merge(base: dict, override: dict):
    """递归合并两个字典"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
