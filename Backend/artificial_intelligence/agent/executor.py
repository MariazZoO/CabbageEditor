"""
Agent 执行模块
负责 Agent 的创建、运行和备用完成逻辑
"""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import BaseMessage, SystemMessage
from langchain.agents import create_agent

from Backend.artificial_intelligence.config.ai_config import AIConfig, get_ai_config
from Backend.artificial_intelligence.models import get_chat_model
from Backend.artificial_intelligence.tools import load_tools


_CACHED_AGENT: Any = None


def _build_agent(config: AIConfig) -> Any:
    """构建 Agent 实例（内部函数）"""
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
    """创建或获取缓存的默认 Agent"""
    global _CACHED_AGENT
    if _CACHED_AGENT is None or force_reload:
        _CACHED_AGENT = _build_agent(get_ai_config())
    return _CACHED_AGENT


def run_agent(messages: List[BaseMessage]) -> Dict[str, Any]:
    """
    运行 agent，接受标准的 LangChain BaseMessage 列表

    Args:
        messages: LangChain BaseMessage 列表（HumanMessage, AIMessage 等）

    Returns:
        Agent 执行结果 {"messages": [...]}
    """
    agent = create_default_agent()
    return agent.invoke({"messages": messages})


def fallback_completion(history: List[BaseMessage]) -> str:
    """
    备用完成方法：直接使用 LLM 而不经过 agent

    Args:
        history: 对话历史

    Returns:
        LLM 生成的文本内容
    """
    cfg = get_ai_config()
    chat_cfg = cfg.chat
    llm = get_chat_model(
        cfg,
        provider_name=chat_cfg.provider,
        model_name=chat_cfg.model,
        temperature=chat_cfg.temperature,
        request_timeout=chat_cfg.request_timeout,
    )

    # 添加系统提示
    prompt_messages: List[BaseMessage] = [
        SystemMessage(content=chat_cfg.system_prompt),
        *history,
    ]

    ai_message = llm.invoke(prompt_messages)
    content = ai_message.content or ""

    # content 为数组时提取 text
    if isinstance(content, list):
        content = "\n".join([b["text"] for b in content if b.get("type") == "text"])

    print(f"[Fallback] {content}")
    return content


__all__ = [
    "create_default_agent",
    "run_agent",
    "fallback_completion",
]
