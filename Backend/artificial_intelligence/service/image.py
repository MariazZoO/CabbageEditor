from __future__ import annotations

import json
from typing import Any, Dict

from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    extract_latest_user_content,
    extract_parameter,
    make_error,
    make_response,
    session_context,
)


def handle_image_generation(payload: Any) -> str:
    """
    处理独立的图像生成请求。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        session_id = request_data.get("session_id")

        # 提取 prompt
        prompt = ""
        user_content = extract_latest_user_content(request_data)
        if user_content:
            for part in user_content.get("part", []):
                if part.get("content_type") == "text":
                    prompt = part.get("content_text", "")
                    break

        if not prompt:
            prompt = extract_parameter(request_data, "prompt")

        if not prompt:
            raise ValueError("缺少必需参数: prompt")

        product_url = extract_parameter(request_data, "product_url")
        scene_url = extract_parameter(request_data, "scene_url")

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.image_tools import (
            load_image_tools,
        )

        tools = load_image_tools(cfg)
        if not tools:
            raise RuntimeError("图像生成功能未启用或配置不完整")

        image_tool = tools[0]

        with session_context(session_id) as sid:
            result_json = image_tool.func(
                prompt=prompt,
                product_url=product_url,
                scene_url=scene_url,
            )

        tool_result = json.loads(result_json)
        image_url = tool_result.get("image_url", "")

        parts = [
            {
                "content_type": "image",
                "content_url": image_url,
                "parameter": {
                    "resolution": tool_result.get(
                        "resolution", "1:1"
                    )  # 假设默认分辨率
                },
            }
        ]

        # 如果有 prompt 返回，也可以包含
        if tool_result.get("prompt"):
            parts.append(
                {"content_type": "text", "content_text": tool_result.get("prompt")}
            )

        return make_response(
            interface_type="image",
            session_id=sid,
            parts=parts,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "image",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_image_generation"]
