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


def handle_video_generation(payload: Any) -> str:
    """
    处理独立的视频生成请求（图生视频）。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        session_id = request_data.get("session_id")

        # 提取 prompt 和 image_url
        prompt = ""
        image_url = ""
        user_content = extract_latest_user_content(request_data)
        if user_content:
            for part in user_content.get("part", []):
                if part.get("content_type") == "text":
                    prompt = part.get("content_text", "")
                elif part.get("content_type") == "image":
                    image_url = part.get("content_url", "")

        if not prompt:
            prompt = extract_parameter(request_data, "prompt")
        if not image_url:
            image_url = extract_parameter(request_data, "image_url")

        if not prompt:
            raise ValueError("缺少必需参数: prompt")
        if not image_url:
            raise ValueError("缺少必需参数: image_url")

        resolution = extract_parameter(request_data, "resolution", "720P")
        prompt_extend = extract_parameter(request_data, "prompt_extend", True)

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

        parts = []
        if tool_result.get("video_url"):
            parts.append(
                {
                    "content_type": "video",
                    "content_url": tool_result.get("video_url"),
                    "parameter": {
                        "resolution": tool_result.get("resolution", resolution),
                        "duration": tool_result.get("duration"),
                    },
                }
            )

        # 如果有 prompt 返回
        if tool_result.get("prompt"):
            parts.append(
                {"content_type": "text", "content_text": tool_result.get("prompt")}
            )

        metadata = {
            "source": tool_result.get("source", ""),
            "model": tool_result.get("model", ""),
            "task_id": tool_result.get("task_id", ""),
        }

        for optional_field in [
            "orig_prompt",
            "actual_prompt",
            "usage",
            "local_video",
            "download_error",
        ]:
            if optional_field in tool_result:
                metadata[optional_field] = tool_result[optional_field]

        return make_response(
            interface_type="video",
            session_id=sid,
            parts=parts,
            status_info=status if status != "success" else "",
            metadata=metadata,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "video",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_video_generation"]
