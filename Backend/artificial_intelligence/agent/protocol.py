"""
协议转换模块
负责前端 JSON 格式和 LangChain Messages 之间的转换
"""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import AIMessage


def extract_session_id(payload: Any, default_session: str) -> str:
    """从 payload 中提取 session_id"""
    if isinstance(payload, dict):
        return str(payload.get("session_id") or default_session)
    return default_session


def build_user_message(payload: Any) -> List[Dict[str, Any]]:
    """从前端 payload 构建 HumanMessage 的 content 列表"""
    blocks: List[Dict[str, Any]] = []

    # 处理 llm_content 格式
    if isinstance(payload, dict) and "llm_content" in payload:
        llm_content = payload.get("llm_content", [])
        if isinstance(llm_content, list):
            # 找到最后一条用户消息
            for content in reversed(llm_content):
                if content.get("role") == "user":
                    for part in content.get("part", []):
                        content_type = part.get("content_type")
                        if content_type == "text":
                            text = part.get("content_text", "").strip()
                            if text:
                                blocks.append({"type": "text", "text": text})
                        elif content_type == "image":
                            url = part.get("content_url")
                            if url:
                                blocks.append({"type": "image_url", "image_url": {"url": url}})
                    break

    # 处理简单文本格式
    elif isinstance(payload, str):
        blocks.append({"type": "text", "text": payload})

    if not blocks:
        blocks.append({"type": "text", "text": "[空消息]"})

    return blocks


def extract_assistant_messages(messages: List[Any]) -> List[AIMessage]:
    """从 agent 输出中提取 AIMessage 列表"""
    result: List[AIMessage] = []
    
    for msg in messages:
        if isinstance(msg, AIMessage):
            result.append(msg)
        elif isinstance(msg, dict) and msg.get("role") == "assistant":
            content = msg.get("content")
            # 确保 content 为数组
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            result.append(AIMessage(content=content))
    
    return result


__all__ = [
    "extract_session_id",
    "build_user_message",
    "extract_assistant_messages",
]
