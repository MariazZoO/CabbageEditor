from __future__ import annotations

import json
from typing import Any, Dict

from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    make_error,
    make_response,
    require_fields,
    session_context,
)


def handle_image_generation(payload: Any) -> str:
    """
    处理独立的图像生成请求。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        require_fields(request_data, ["prompt"])

        session_id = request_data.get("session_id")
        prompt = request_data.get("prompt")
        product_url = request_data.get("product_url")
        scene_url = request_data.get("scene_url")

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.text import (
            load_text_tools,
        )

        tools = load_text_tools(cfg)
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

        return make_response(
            response_type="image_generation",
            session_id=sid,
            prompt=tool_result.get("prompt", prompt),
            image={
                "name": "",
                "path": "",
                "url": image_url,
                "base64": "",
            },
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "image_generation",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_image_generation"]
