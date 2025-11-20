from __future__ import annotations

from typing import Any, Dict, List

from Backend.artificial_intelligence.agent.conversation import default_session_id
from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    make_error,
    make_response,
    pick_tool,
    session_context,
)


def _extract_instruction(parts: List[Dict[str, Any]]) -> str:
    """从 content 列表中提取文本内容。"""
    instruction = ""
    for item in parts:
        if item.get("type") == "text":
            instruction += item.get("text", "") + "\n"
    return instruction.strip()


def handle_text_generation(payload: Any) -> str:
    """
    处理独立的文本生成请求（原文案生成）。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        text_type = request_data.get("type", "product")
        if text_type not in ["product", "marketing", "creative"]:
            raise ValueError(f"不支持的文案类型: {text_type}")

        session_id = request_data.get("session_id", default_session_id())

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.text import (
            load_text_tools,
        )

        tools = load_text_tools(cfg)
        if not tools:
            raise RuntimeError("文案生成功能未启用或配置不完整")

        tool_map = {
            "product": ["generate_product_text"],
            "marketing": ["generate_marketing_text"],
            "creative": ["generate_creative_text"],
        }

        text_tool = pick_tool(tools, tool_map[text_type])

        instruction = ""
        if "content" in request_data and isinstance(request_data["content"], list):
            instruction = _extract_instruction(request_data["content"])
        if not instruction and "message" in request_data:
            instruction = request_data["message"]

        metadata = request_data.get("metadata", {})
        tool_params: Dict[str, Any] = {"instruction": instruction.strip()}

        if text_type == "product":
            if "style" in metadata:
                tool_params["style"] = metadata["style"]
            if "length" in metadata:
                tool_params["length"] = metadata["length"]
        elif text_type == "marketing":
            if "platform" in metadata:
                tool_params["platform"] = metadata["platform"]
            if "tone" in metadata:
                tool_params["tone"] = metadata["tone"]
        elif text_type == "creative":
            if "style" in metadata:
                tool_params["style"] = metadata["style"]
            if "length" in metadata:
                tool_params["length"] = metadata["length"]

        with session_context(session_id) as sid:
            result = text_tool.func(**tool_params)

        return make_response(
            response_type="text_generation",
            session_id=sid,
            text_type=text_type,
            content=result,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "text_generation",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_text_generation"]
