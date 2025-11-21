from __future__ import annotations

import json
from typing import Any, Dict

from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_multilayer_error,
    build_multilayer_success,
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
        tool_result = json.loads(result_json)

        # 检查工具返回的业务错误
        if "error" in tool_result and tool_result["error"]:
            raise RuntimeError(f"图像生成失败: {tool_result['error']}")
        if tool_result.get("status") == "failed":
            error_msg = tool_result.get("error", "未知错误")
            raise RuntimeError(f"图像生成失败: {error_msg}")

        image_url = tool_result.get("image_url", "")
        if not image_url:
            raise RuntimeError("图像生成未返回有效的 URL")

        parts = [
            {
                "content_type": "image",
                "content_url": image_url,
                "parameter": {
                    "prompt": tool_result.get("prompt", prompt),
                    "resolution": tool_result.get("resolution"),
                },
            }
        ]
        return build_multilayer_success(
            interface_type="image",
            session_id=session_id,
            metadata=metadata,
            parts=parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_multilayer_error(
            interface_type="image",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_image_generation"]
