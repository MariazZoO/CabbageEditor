from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from Backend.artificial_intelligence.agent.requests import IncomingRequest


def extract_text(messages: List[Any]) -> str:
    if not messages:
        return ""
    last = messages[-1]
    # content为数组，拼接所有text类型内容
    if isinstance(last, BaseMessage):
        content = last.content
    elif isinstance(last, dict):
        content = last.get("content")
    else:
        content = last
    if isinstance(content, list):
        return "\n".join([b["text"] for b in content if b.get("type") == "text"])
    if isinstance(content, str):
        return content
    return str(content)


def build_user_message(request: IncomingRequest) -> Dict[str, Any]:
    blocks: List[Dict[str, Any]] = []
    text = request.text.strip()
    if text:
        blocks.append({"type": "text", "text": text})
    # 添加图片附件为image_url类型（符合OpenAI API规范）
    for attachment in request.images:
        image_url = None
        # 优先使用 data（base64），其次使用 url
        if attachment.data:
            # 如果已经是 data URI 格式，直接使用
            if attachment.data.startswith("data:image"):
                image_url = attachment.data
            else:
                # 否则假设是 base64 编码，添加前缀
                image_url = f"data:image/png;base64,{attachment.data}"
        elif attachment.url:
            # 直接使用 URL（可能是 http:// 或其他格式）
            image_url = attachment.url

        if image_url:
            blocks.append({"type": "image_url", "image_url": {"url": image_url}})
    
    if not blocks:
        blocks.append({"type": "text", "text": "[图片上传]"})
    # 只允许text和image_url类型
    blocks = [b for b in blocks if b.get("type") in ("text", "image_url")]
    return {"role": "user", "content": blocks}


def coerce_messages(state: Any) -> List[Any]:
    """从 agent 输出中提取消息列表"""
    if isinstance(state, dict):
        messages = state.get("messages", [])
    else:
        messages = state
    if isinstance(messages, list):
        return messages
    if messages is None:
        return []
    return [messages]


def render_message_content(content: Any) -> str:
    if isinstance(content, str):
        return summarize_payload_text(content)
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(str(block["text"]))
                elif block.get("type") == "image_url":
                    # 支持标准格式: {"type": "image_url", "image_url": {"url": "..."}}
                    image_url_data = block.get("image_url")
                    if isinstance(image_url_data, dict):
                        url = image_url_data.get("url")
                        if url:
                            parts.append(f"[image] {url}")
                    elif isinstance(image_url_data, str):
                        # 兼容旧格式: {"type": "image_url", "image_url": "..."}
                        parts.append(f"[image] {image_url_data}")
                elif block.get("type") == "image" and block.get("url"):
                    # 兼容旧格式
                    parts.append(f"[image] {block['url']}")
                elif block.get("type") == "image" and block.get("base64"):
                    parts.append("[image]")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join([item for item in parts if item])
    if content is None:
        return ""
    return summarize_payload_text(str(content))


def extract_image_payload(messages: Sequence[Any]) -> Dict[str, Any] | None:
    ordered = list(messages)
    for message in reversed(ordered):
        if isinstance(message, ToolMessage):
            content = render_message_content(message.content)
            try:
                data = json.loads(content)
            except Exception:
                continue
            if isinstance(data, dict) and data.get("type") == "image":
                # 直接返回工具返回的数据，不再进行额外转换
                return data
    return None


def summarize_payload_text(text: str, strip_images: bool = False) -> str:
    text = text.strip()
    if not text:
        return text
    if text.startswith("{") and '"image_base64"' in text:
        try:
            data = json.loads(text)
        except Exception:
            if strip_images:
                return "[image payload omitted]"
            return text
        if isinstance(data, dict) and "image_base64" in data:
            name = (
                data.get("image_name")
                or data.get("image_path")
                or data.get("prompt")
                or "image"
            )
            data = dict(data)
            data.pop("image_base64", None)
            summary = f"[image payload: {name}]"
            return json.dumps(data, ensure_ascii=False) if not strip_images else summary
    if strip_images and "data:image" in text:
        return "[image payload omitted]"
    return text


def log_ai_messages(payload: Any) -> None:
    messages = None
    if isinstance(payload, dict):
        messages = payload.get("messages")
    elif isinstance(payload, list):
        messages = payload
    if not isinstance(messages, list):
        return
    for msg in messages:
        if isinstance(msg, AIMessage):
            text = render_message_content(msg.content)
            print(f"[AIMessage] {text}")
        elif isinstance(msg, ToolMessage):
            text = render_message_content(msg.content)
            tool_name = getattr(msg, "name", None) or "tool"
            print(f"[ToolMessage:{tool_name}] {text}")


def _message_type_to_role(value: str | None) -> str:
    """将 BaseMessage 的类型字段映射到标准的 role 字段"""
    mapping = {
        "human": "user",
        "user": "user",
        "ai": "assistant",
        "assistant": "assistant",
        "system": "system",
        "tool": "tool",
        "function": "tool",
    }
    return mapping.get((value or "").lower(), value or "assistant")


__all__ = [
    "extract_text",
    "build_user_message",
    "coerce_messages",
    "render_message_content",
    "extract_image_payload",
    "summarize_payload_text",
    "log_ai_messages",
]
