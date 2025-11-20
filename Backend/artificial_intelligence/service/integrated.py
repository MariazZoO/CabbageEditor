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
    make_error,
    make_response,
)


def handle_integrated_entrance(payload: Any) -> str:
    """
    统一的聊天接口，支持文本 + 图片。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)

    try:
        result = process_chat_request(request_data)
        messages = result["messages"]
        session_id = result["session_id"]
        pending_history = result["pending_history"]

        content = extract_text(messages)
        if not content.strip():
            content = fallback_completion(pending_history)

        image_payload = extract_image_payload(messages)

        parts = []
        if content:
            parts.append({"content_type": "text", "content_text": content})

        if image_payload:
            image_part = {
                "content_type": "image",
                "content_url": image_payload.get("image_url") or "",
                # 如果有 base64，可能需要处理，但 llms.txt 主要是 content_url
            }
            # 如果有其他参数，可以放入 parameter
            parts.append(image_part)

        metadata = request_data.get("metadata", {})

        return make_response(
            interface_type="integrated",
            session_id=session_id,
            parts=parts,
            metadata=metadata,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error("integrated", request_data.get("session_id"), exc)


__all__ = ["handle_integrated_entrance"]
