from __future__ import annotations

from typing import Any, Dict, List

from Backend.artificial_intelligence.agent.conversation import default_session_id
from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    extract_latest_user_content,
    extract_parameter,
    make_error,
    make_response,
    pick_tool,
    session_context,
)


def _extract_instruction(parts: List[Dict[str, Any]]) -> str:
    """从 content 列表中提取文本内容。"""
    instruction = ""
    for item in parts:
        if item.get("content_type") == "text":
            instruction += item.get("content_text", "") + "\n"
    return instruction.strip()


def handle_text_generation(payload: Any) -> str:
    """
    处理独立的文本生成请求（原文案生成）。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        text_type = extract_parameter(request_data, "text_type", "product")
        # 兼容旧参数名 type
        if not text_type or text_type == "product":  # default
            old_type = extract_parameter(request_data, "type")
            if old_type:
                text_type = old_type

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
        user_content = extract_latest_user_content(request_data)
        if user_content:
            instruction = _extract_instruction(user_content.get("part", []))

        if not instruction:
            # 兼容旧格式
            if "content" in request_data and isinstance(request_data["content"], list):
                # 旧格式 content 也是 list，但结构不同，这里简单处理，假设已经转换或者直接取 message
                pass
            if "message" in request_data:
                instruction = request_data["message"]

        metadata = request_data.get("metadata", {})
        tool_params: Dict[str, Any] = {"instruction": instruction.strip()}

        # 提取参数，优先从 parameter 提取，其次 metadata
        if text_type == "product":
            tool_params["style"] = extract_parameter(request_data, "style", metadata.get("style"))
            tool_params["length"] = extract_parameter(request_data, "length", metadata.get("length"))
        elif text_type == "marketing":
            tool_params["platform"] = extract_parameter(request_data, "platform", metadata.get("platform"))
            tool_params["tone"] = extract_parameter(request_data, "tone", metadata.get("tone"))
        elif text_type == "creative":
            tool_params["style"] = extract_parameter(request_data, "style", metadata.get("style"))
            tool_params["length"] = extract_parameter(request_data, "length", metadata.get("length"))

        with session_context(session_id) as sid:
            result = text_tool.func(**tool_params)

        parts = [{
            "content_type": "text",
            "content_text": result,
            "parameter": {
                "text_type": text_type
            }
        }]

        return make_response(
            interface_type="text",
            session_id=sid,
            parts=parts,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "text",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_text_generation"]
