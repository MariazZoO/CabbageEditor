from __future__ import annotations

import json
from typing import Any, Dict

from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
    session_context,
)


def _extract_prompt_from_llm_content(data: Dict[str, Any]) -> str:
    llm_content = data.get("llm_content")
    if not isinstance(llm_content, list) or not llm_content:
        return data.get("prompt", "")
    first = llm_content[0]
    parts = first.get("part", [])
    prompt = "".join(
        p.get("content_text", "") for p in parts if p.get("content_type") == "text"
    ).strip()
    return prompt


def handle_image_generation(payload: Any) -> str:
    """图像生成，返回三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    session_id = request_data.get("session_id") or "default"
    metadata = request_data.get("metadata", {})
    try:
        prompt = _extract_prompt_from_llm_content(request_data)
        if not prompt:
            raise ValueError("缺少图像生成的 prompt")

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.image_tools import (
            load_image_tools,
        )

        tools = load_image_tools(cfg)
        if not tools:
            raise RuntimeError("图像生成功能未启用或配置不完整")

        image_tool = tools[0]
        with session_context(session_id) as sid:
            result_json = image_tool.func(prompt=prompt)
            session_id = sid  # 使用实际上下文 session

        # 解析 Tool 返回的 Envelope JSON
        tool_envelope = json.loads(result_json)

        # 检查错误
        if tool_envelope.get("error_code", 0) != 0:
            error_msg = tool_envelope.get("status_info", "未知错误")
            raise RuntimeError(f"图像生成失败: {error_msg}")

        # 提取 llm_content
        llm_content = tool_envelope.get("llm_content", [])
        if not llm_content:
            raise RuntimeError("图像生成未返回有效内容")

        # 提取并清洗 parts
        original_parts = llm_content[0].get("part", [])
        cleaned_parts = []
        for part in original_parts:
            cleaned_part = {
                "content_type": part.get("content_type"),
                "content_url": part.get("content_url"),
                "content_text": part.get("content_text"),
            }
            # 严格过滤 parameter
            if "parameter" in part:
                original_param = part["parameter"]
                cleaned_param = {}
                if "resolution" in original_param:
                    cleaned_param["resolution"] = original_param["resolution"]
                if cleaned_param:
                    cleaned_part["parameter"] = cleaned_param

            # 移除 None 值字段
            cleaned_part = {k: v for k, v in cleaned_part.items() if v is not None}
            cleaned_parts.append(cleaned_part)

        if not cleaned_parts:
            raise RuntimeError("图像生成未返回有效的图片部分")

        return build_success_response(
            interface_type="image",
            session_id=session_id,
            metadata=metadata,
            parts=cleaned_parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_error_response(
            interface_type="image",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_image_generation"]
