"""
Agent 统一接口
对外暴露的唯一入口
"""

from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import HumanMessage

from Backend.artificial_intelligence.agent.executor import run_agent, fallback_completion
from Backend.artificial_intelligence.agent.conversation import (
    default_session_id,
    get_history,
    update_history,
)
from Backend.artificial_intelligence.agent.protocol import (
    extract_session_id,
    build_user_message,
    extract_assistant_messages,
)
from Backend.artificial_intelligence.service.context import (
    reset_current_session,
    set_current_session,
)


def process_chat_request(payload: Any) -> Dict[str, Any]:
    """
    处理聊天请求的核心逻辑

    Args:
        payload: 前端请求数据

    Returns:
        包含 messages, session_id, pending_history 的字典
    """
    # 提取 session_id 和历史记录
    session_id = extract_session_id(payload, default_session_id())
    stored_history = get_history(session_id)

    # 构建当前用户消息
    content = build_user_message(payload)
    pending_history = [
        *stored_history,
        HumanMessage(content=content),
    ]

    # 在 session 上下文中运行 agent
    token = set_current_session(session_id)
    try:
        state = run_agent(pending_history)
    finally:
        reset_current_session(token)

    # 提取返回的消息
    messages = state.get("messages", [])

    # 提取 AIMessage 并更新历史
    history_extension = extract_assistant_messages(messages)
    if history_extension:
        update_history(session_id, [*pending_history, *history_extension])
    else:
        # 如果没有 AIMessage，使用 fallback
        fallback_text = fallback_completion(pending_history)
        if fallback_text:
            from langchain_core.messages import AIMessage

            history_extension = [AIMessage(content=fallback_text)]
            update_history(session_id, [*pending_history, *history_extension])

    return {
        "messages": messages,
        "session_id": session_id,
        "pending_history": pending_history,
    }


__all__ = [
    "process_chat_request",
]
