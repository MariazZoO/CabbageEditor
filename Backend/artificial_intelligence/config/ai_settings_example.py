from __future__ import annotations

from typing import Any, Dict

DEFAULT_SYSTEM_PROMPT = (
    "你是 CabbageEditor 的内置助手。请在回答前检查可用工具，不要编造答案。"
    "必要时调用 MCP、图像或视频工具。回答时用中文简洁回答。"
)

AI_SETTINGS: Dict[str, Any] = {
    "runtime": {
        "enable_gpu": False,
        "log_level": "INFO",
    },
    "providers": [
        {
            "name": "siliconflow",
            "type": "openai-compatible",
            "base_url": "https://api.siliconflow.cn/v1",
            "api_key": "sk-xxxxx",
        },
        {
            "name": "closeai",
            "type": "openai-compatible",
            "base_url": "https://api.openai-proxy.org/v1",
            "api_key": "sk-xxxxx",
        },
        {
            "name": "lingya",
            "type": "openai-compatible",
            "base_url": "https://api.lingyaai.cn/v1",
            "api_key": "sk-xxxxx",
        },
        {
            "name": "dashscope",
            "type": "dashscope",
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "api_key": "sk-xxxxx",
        },
        {
            "name": "doubao",
            "type": "openai-compatible",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "api_key": "sk-your-doubao-key",
        },
    ],
    "llm": {
        "chat": {
            "provider": "siliconflow",
            "model": "deepseek-ai/DeepSeek-V3.2-Exp",
            "temperature": 0.2,
            "request_timeout": 60,
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
        },
        "tool_models": {
            "mcp": {
                "provider": "siliconflow",
                "model": "deepseek-ai/DeepSeek-V3.2-Exp",
            }
        },
    },
    "media": {
        "image": {
            "enable": True,
            "provider": "lingya",
            "model": "nano-banana",
            "base_url": "https://api.lingyaai.cn/v1/images/generations",
        },
        "video": {
            "enable": True,
            "provider": "dashscope",
            "model": "wan2.2-i2v-flash",
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
        },
    },
    "tts": {
        # 火山引擎 TTS 配置
        # 获取方式: https://www.volcengine.com/docs/6561/196768
        "appid": "your-tts-appid",
        "token": "your-tts-token",
    },
    "music": {
        # Suno API 配置 (文本到背景音乐 BGM 生成)
        # 获取方式: https://www.sunoapi.org
        "api_key": "your-key",
        "base_url": "https://api.sunoapi.org",
    },
}
