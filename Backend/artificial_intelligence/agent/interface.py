"""
Agent 统一接口
对外暴露的唯一入口，负责协议转换和异常处理
"""
from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage

from Backend.artificial_intelligence.agent.agent_core import run_agent
from Backend.artificial_intelligence.agent.conversation import (
    default_session_id,
    get_history,
    update_history,
)
from Backend.artificial_intelligence.agent.adapters import (
    build_user_message,
    coerce_messages,
    log_ai_messages,
    normalize_request,
)
from Backend.artificial_intelligence.tools.session import (
    reset_current_session,
    set_current_session,
)


def process_chat_request(payload: Any) -> Dict[str, Any]:
    """
    处理聊天请求的核心逻辑，返回处理结果字典

    接受两种输入格式：
    1. 用户消息（带图片上传）
    2. 简单文本消息

    返回包含以下内容的字典：
    {
        "messages": [...],           # agent 返回的消息列表
        "session_id": "...",         # 会话ID
        "pending_history": [...]     # 用于 fallback 的历史记录
    }
    """
    # 规范化请求并获取历史记录
    request = normalize_request(payload, default_session_id())
    stored_history = get_history(request.session_id)

    user_message = build_user_message(request)
    # user_message为dict，需转为BaseMessage
    pending_history = [
        *stored_history,
        HumanMessage(content=user_message["content"]),
    ]

    token = set_current_session(request.session_id)
    try:
        # 直接调用 agent
        state = run_agent(pending_history)
        log_ai_messages(state)
    finally:
        reset_current_session(token)

    messages = coerce_messages(state)
    # messages为dict列表，提取assistant消息并转为AIMessage
    history_extension = []
    for m in messages:
        if isinstance(m, dict) and m.get("role") == "assistant":
            content = m.get("content")
            # 确保content为数组
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            history_extension.append(AIMessage(content=content))
        elif isinstance(m, AIMessage):
            history_extension.append(m)
    update_history(request.session_id, [*pending_history, *history_extension])

    return {
        "messages": messages,
        "session_id": request.session_id,
        "pending_history": pending_history,
    }


__all__ = [
    "process_chat_request",
]
