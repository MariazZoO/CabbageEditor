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

        response_type = (
            image_payload.get("type", "ai_response") if image_payload else "ai_response"
        )

        extra: Dict[str, Any] = {"content": content}
        if image_payload:
            extra.update(
                {
                    "image_base64": image_payload.get("image_base64"),
                    "image_name": image_payload.get("image_name"),
                    "image_path": image_payload.get("image_path"),
                    "image_url": image_payload.get("image_url"),
                }
            )

        return make_response(
            response_type=response_type,
            session_id=session_id,
            **extra,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error("ai_response", request_data.get("session_id"), exc)


__all__ = ["handle_integrated_entrance"]
