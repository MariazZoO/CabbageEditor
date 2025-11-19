from __future__ import annotations

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from Backend.artificial_intelligence.config.ai_config import ProviderConfig


def build_openai_chat(
    provider: ProviderConfig,
    *,
    model: str,
    temperature: float,
    request_timeout: float,
) -> BaseChatModel:
    if not provider.api_key:
        raise RuntimeError(f"Provider '{provider.name}' 缺少 API Key，无法创建 ChatOpenAI 模型。")
    return ChatOpenAI(
        model=model,
        api_key=provider.api_key,
        base_url=provider.base_url,
        default_headers=provider.headers or None,
        temperature=temperature,
        timeout=request_timeout,
    )


__all__ = ["build_openai_chat"]
