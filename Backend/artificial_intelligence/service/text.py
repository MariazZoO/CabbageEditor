from __future__ import annotations

import json
from typing import Any, Dict, List

from Backend.artificial_intelligence.agent.conversation import default_session_id
from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
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


def _extract_prompt_from_llm_content(data: Dict[str, Any]) -> str:
    llm_content = data.get("llm_content")
    if not isinstance(llm_content, list) or not llm_content:
        return ""
    first = llm_content[0]
    parts = first.get("part", [])
    prompt = "\n".join(
        p.get("content_text", "") for p in parts if p.get("content_type") == "text"
    ).strip()
    return prompt


def handle_text_generation(payload: Any) -> str:
    """文本生成三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    metadata = request_data.get("metadata", {})
    session_id = request_data.get("session_id", default_session_id())
    try:
        text_type = request_data.get("type", "product")
        if text_type not in ["product", "marketing", "creative"]:
            raise ValueError(f"不支持的文案类型: {text_type}")

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.text import load_text_tools

        tools = load_text_tools(cfg)
        if not tools:
            raise RuntimeError("文案生成功能未启用或配置不完整")
        tool_map = {
            "product": ["generate_product_text"],
            "marketing": ["generate_marketing_text"],
            "creative": ["generate_creative_text"],
        }
        text_tool = pick_tool(tools, tool_map[text_type])

        instruction = _extract_prompt_from_llm_content(request_data)
        if not instruction and "message" in request_data:
            instruction = request_data["message"]

        if not instruction or not instruction.strip():
            raise ValueError("缺少文本生成的指令内容")

        tool_params: Dict[str, Any] = {"instruction": instruction.strip()}

        with session_context(session_id) as sid:
            result_json = text_tool.func(**tool_params)
            session_id = sid

        # 解析 Tool 返回的 Envelope JSON
        tool_envelope = json.loads(result_json)

        # 检查错误
        if tool_envelope.get("error_code", 0) != 0:
            error_msg = tool_envelope.get("status_info", "未知错误")
            raise RuntimeError(f"文案生成失败: {error_msg}")

        # 提取 llm_content
        llm_content = tool_envelope.get("llm_content", [])
        if not llm_content:
            raise RuntimeError("文案生成未返回有效内容")

        # 提取并清洗 parts
        original_parts = llm_content[0].get("part", [])
        cleaned_parts = []
        for part in original_parts:
            cleaned_part = {
                "content_type": part.get("content_type"),
                "content_text": part.get("content_text"),
            }
            # 严格过滤 parameter
            if "parameter" in part:
                original_param = part["parameter"]
                cleaned_param = {}
                if "text_type" in original_param:
                    cleaned_param["text_type"] = original_param["text_type"]
                if cleaned_param:
                    cleaned_part["parameter"] = cleaned_param

            # 移除 None 值字段
            cleaned_part = {k: v for k, v in cleaned_part.items() if v is not None}
            cleaned_parts.append(cleaned_part)

        if not cleaned_parts:
            raise RuntimeError("文案生成未返回有效的文本部分")

        return build_success_response(
            interface_type="text",
            session_id=session_id,
            metadata=metadata,
            parts=cleaned_parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_error_response(
            interface_type="text",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_text_generation"]
