from __future__ import annotations

from typing import Any

from langchain.agents import create_agent

from Backend.artificial_intelligence.config.ai_config import AIConfig, get_ai_config
from Backend.artificial_intelligence.models import get_chat_model
from Backend.artificial_intelligence.tools import load_tools

_CACHED_AGENT: Any = None


def _build_agent(config: AIConfig) -> Any:
    chat_cfg = config.chat
    llm = get_chat_model(
        config,
        provider_name=chat_cfg.provider,
        model_name=chat_cfg.model,
        temperature=chat_cfg.temperature,
        request_timeout=chat_cfg.request_timeout,
    )
    tools = load_tools(config)
    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=chat_cfg.system_prompt,
    )


def create_default_agent(force_reload: bool = False) -> Any:
    global _CACHED_AGENT
    if _CACHED_AGENT is None or force_reload:
        _CACHED_AGENT = _build_agent(get_ai_config())
    return _CACHED_AGENT


__all__ = ["create_default_agent"]
