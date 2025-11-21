from __future__ import annotations

import time
from typing import Any, Dict, List

from langchain_core.messages import AIMessage

from Backend.artificial_intelligence.agent.agent_core import fallback_completion
from Backend.artificial_intelligence.agent.interface import process_chat_request

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
)


def _extract_assistant_content(msg: AIMessage) -> List[Dict[str, Any]]:
    """从 AIMessage 提取 part 列表"""
    parts: List[Dict[str, Any]] = []

    if isinstance(msg.content, str):
        parts.append({"content_type": "text", "content_text": msg.content})
    elif isinstance(msg.content, list):
        for block in msg.content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(
                        {
                            "content_type": "text",
                            "content_text": block.get("text"),
                        }
                    )

    return parts


def handle_integrated_entrance(payload: Any) -> str:
    """统一聊天接口 - 只返回最后一条 Assistant 消息"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    metadata = request_data.get("metadata", {})

    try:
        # 验证输入
        llm_content = request_data.get("llm_content", [])
        if not isinstance(llm_content, list) or not llm_content:
            raise ValueError("llm_content 不能为空")

        # 调用 agent，获取标准 Messages
        result = process_chat_request(request_data)
        messages = result["messages"]
        session_id = result["session_id"]
        pending_history = result["pending_history"]

        # 查找最后一条 AIMessage
        last_ai_message = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                last_ai_message = msg
                break

        # 如果没有找到 AIMessage，使用 fallback
        if last_ai_message is None:
            content = fallback_completion(pending_history)
            if not content:
                raise ValueError("Agent 未返回有效响应")

            parts = [{"content_type": "text", "content_text": content}]
        else:
            parts = _extract_assistant_content(last_ai_message)
            if not parts:
                raise ValueError("Assistant 消息内容为空")

        # 构建响应
        llm_content_list = [
            {
                "role": "assistant",
                "interface_type": "integrated",
                "sent_time_stamp": int(time.time()),
                "part": parts,
            }
        ]

        return build_success_response(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            llm_content=llm_content_list,
        )

    except Exception as exc:  # noqa: BLE001
        session_id = request_data.get("session_id", "default")
        return build_error_response(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_integrated_entrance"]
