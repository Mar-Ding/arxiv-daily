"""
LLM 引擎模块 — DeepSeek API 调用
"""

import json
import sys
import urllib.request
import urllib.error
from typing import Optional

from .config import load_config


def call_deepseek(messages: list[dict], api_key: str = None,
                  base_url: str = None, model: str = None,
                  temperature: float = 0.3, max_tokens: int = 4096) -> str:
    """Call DeepSeek Chat API with OpenAI-compatible endpoint."""
    config = load_config()
    ds_cfg = config['llm']['deepseek']
    api_key = api_key or ds_cfg['api_key']
    base_url = base_url or ds_cfg['base_url']
    model = model or ds_cfg['model']

    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY 未设置！请通过环境变量或config.yaml配置")

    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except urllib.error.HTTPError as e:
        print(f"DeepSeek API error ({e.code}): {e.read().decode()}",
              file=sys.stderr)
        raise
    except Exception as e:
        print(f"DeepSeek API call failed: {e}", file=sys.stderr)
        raise
