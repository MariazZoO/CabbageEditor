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


def handle_video_generation(payload: Any) -> str:
    """
    处理独立的视频生成请求（图生视频）。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        require_fields(request_data, ["prompt", "image_url"])

        prompt = request_data.get("prompt")
        image_url = request_data.get("image_url")
        session_id = request_data.get("session_id")
        resolution = request_data.get("resolution", "720P")
        prompt_extend = request_data.get("prompt_extend", True)

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.video_tools import (
            load_video_tools,
        )

        tools = load_video_tools(cfg)
        if not tools:
            raise RuntimeError("视频生成功能未启用或配置不完整")

        video_tool = tools[0]

        with session_context(session_id) as sid:
            result_json = video_tool.func(
                prompt=prompt,
                image_url=image_url,
                resolution=resolution,
                prompt_extend=prompt_extend,
            )

        tool_result = json.loads(result_json)
        status = (
            "success"
            if tool_result.get("status") == "succeeded"
            else tool_result.get("status", "success")
        )

        response_body = {
            "prompt": tool_result.get("prompt", prompt),
            "source": tool_result.get("source", ""),
            "model": tool_result.get("model", ""),
            "video_url": tool_result.get("video_url", ""),
            "task_id": tool_result.get("task_id", ""),
            "resolution": tool_result.get("resolution", resolution),
        }

        for optional_field in [
            "orig_prompt",
            "actual_prompt",
            "usage",
            "local_video",
            "download_error",
        ]:
            if optional_field in tool_result:
                response_body[optional_field] = tool_result[optional_field]

        return make_response(
            response_type="video_generation",
            status=status,
            session_id=sid,
            **response_body,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "video_generation",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_video_generation"]
