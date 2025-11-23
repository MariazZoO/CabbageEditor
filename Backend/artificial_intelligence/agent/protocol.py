# file: Backend/artificial_intelligence/agent/protocol.py

from __future__ import annotations
import json
import uuid
import time
from typing import Any, Dict, List
from langchain_core.messages import AIMessage, ToolMessage

# [配置] 开启人工工具构造模式
USE_ARTIFICIAL_TOOL_FOR_MEDIA = True


def extract_session_id(payload: Any, default_session: str) -> str:
    if isinstance(payload, dict):
        return str(payload.get("session_id") or default_session)
    return default_session


def extract_user_parts(payload: Any) -> List[Dict[str, Any]]:
    """提取用户输入中的 part 列表 (保持原逻辑)"""
    if isinstance(payload, dict) and "llm_content" in payload:
        llm_content = payload.get("llm_content", [])
        if isinstance(llm_content, list):
            for content in reversed(llm_content):
                if content.get("role") == "user":
                    return list(content.get("part", []))
    if isinstance(payload, str):
        return [{"content_type": "text", "content_text": payload}]
    return []


def wrap_part_as_tool_message(part: Dict[str, Any], session_id: str) -> ToolMessage:
    """
    将 part 封装为工具消息。
    构造一个符合 llms.txt 定义的完整 API 响应结构作为 content。

    Args:
        part: 媒体资源部分
        session_id: 当前会话ID (关键修正)
    """
    call_id = f"call_upload_{uuid.uuid4().hex[:8]}"

    envelope = {
        "session_id": session_id,
        "error_code": 0,
        "status_info": "success",
        "llm_content": [
            {
                "role": "tool",
                "interface_type": part.get("content_type", "unknown"),
                "sent_time_stamp": int(time.time()),
                "part": [part],
            }
        ],
        "metadata": {"source": "user_attachment"},
    }

    # 序列化整个 Envelope
    json_content = json.dumps(envelope, ensure_ascii=False)

    return ToolMessage(content=json_content, tool_call_id=call_id, name="upload_attachment_tool")


def extract_assistant_messages(messages: List[Any]) -> List[AIMessage]:
    result: List[AIMessage] = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            result.append(msg)
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            result.append(AIMessage(content=content))
    return result


__all__ = [
    "extract_session_id",
    "extract_user_parts",
    "wrap_part_as_tool_message",
    "extract_assistant_messages",
    "USE_ARTIFICIAL_TOOL_FOR_MEDIA",
]
