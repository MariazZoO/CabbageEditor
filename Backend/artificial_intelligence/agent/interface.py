# file: Backend/artificial_intelligence/agent/interface.py

from __future__ import annotations
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from Backend.artificial_intelligence.agent.executor import run_agent, fallback_completion
from Backend.artificial_intelligence.agent.conversation import (
    default_session_id,
    get_history,
    update_history,
)
from Backend.artificial_intelligence.agent.protocol import (
    extract_session_id,
    extract_assistant_messages,
    extract_user_parts,
    wrap_part_as_tool_message,
    USE_ARTIFICIAL_TOOL_FOR_MEDIA,
)
from Backend.artificial_intelligence.service.context import (
    reset_current_session,
    set_current_session,
)


def process_chat_request(payload: Any) -> Dict[str, Any]:
    # 1. 提取 Session ID
    session_id = extract_session_id(payload, default_session_id())
    stored_history = get_history(session_id)

    # 2. 获取原始输入 parts
    raw_parts = extract_user_parts(payload)

    human_content_blocks: List[Dict[str, Any]] = []
    artificial_tool_messages: List[ToolMessage] = []

    # 3. 分流处理
    for part in raw_parts:
        c_type = part.get("content_type")

        if c_type == "text":
            text = part.get("content_text", "").strip()
            if text:
                human_content_blocks.append({"type": "text", "text": text})

        elif c_type in ["image", "video", "audio"]:
            url = part.get("content_url")
            if url:
                if USE_ARTIFICIAL_TOOL_FOR_MEDIA:
                    # [修正] 传入 session_id，确保伪造工具消息的上下文正确
                    tool_msg = wrap_part_as_tool_message(part, session_id)
                    artificial_tool_messages.append(tool_msg)
                else:
                    if c_type == "image":
                        human_content_blocks.append(
                            {"type": "image_url", "image_url": {"url": url}}
                        )

    if not human_content_blocks:
        human_content_blocks.append({"type": "text", "text": "[Attachment Uploaded]"})

    current_human_message = HumanMessage(content=human_content_blocks)

    pending_history = [
        *stored_history,
        *artificial_tool_messages,
        current_human_message,
    ]

    token = set_current_session(session_id)
    try:
        state = run_agent(pending_history)
    finally:
        reset_current_session(token)

    messages = state.get("messages", [])

    history_extension = extract_assistant_messages(messages)

    new_entries = [*artificial_tool_messages, current_human_message]

    if history_extension:
        new_entries.extend(history_extension)
        update_history(session_id, [*stored_history, *new_entries])
    else:
        fallback_text = fallback_completion(pending_history)
        if fallback_text:
            history_extension = [AIMessage(content=fallback_text)]
            new_entries.extend(history_extension)
            update_history(session_id, [*stored_history, *new_entries])

    return {
        "messages": messages,
        "session_id": session_id,
        "pending_history": pending_history,
    }


__all__ = ["process_chat_request"]
