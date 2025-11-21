from __future__ import annotations

from typing import Any, Dict

from Backend.artificial_intelligence.agent.agent_core import fallback_completion
from Backend.artificial_intelligence.agent.adapters import (
    extract_image_payload,
    extract_text,
)
from Backend.artificial_intelligence.agent.interface import process_chat_request

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_multilayer_error,
    build_multilayer_success,
)


def handle_integrated_entrance(payload: Any) -> str:
    """统一聊天接口三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    metadata = request_data.get("metadata", {})
    try:
        # 提前验证输入
        llm_content = request_data.get("llm_content", [])
        if not isinstance(llm_content, list) or not llm_content:
            raise ValueError("llm_content 不能为空")
        
        result = process_chat_request(request_data)
        messages = result["messages"]
        session_id = result["session_id"]
        pending_history = result["pending_history"]
        content = extract_text(messages)
        if not content.strip():
            content = fallback_completion(pending_history)

        # 验证至少有内容或图片
        image_payload = extract_image_payload(messages)
        if not content.strip() and not image_payload:
            raise ValueError("请求中既没有文本内容也没有图片")

        parts = []
        if content:
            parts.append({"content_type": "text", "content_text": content})
        if image_payload:
            parts.append(
                {
                    "content_type": "image",
                    "content_url": image_payload.get("image_url") or "",
                }
            )
        return build_multilayer_success(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            parts=parts,
        )
    except Exception as exc:  # noqa: BLE001
        session_id = request_data.get("session_id", "default")
        return build_multilayer_error(
            interface_type="integrated",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_integrated_entrance"]
