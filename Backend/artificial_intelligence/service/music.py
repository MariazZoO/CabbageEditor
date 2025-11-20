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


def handle_music_generation(payload: Any) -> str:
    """
    处理独立的BGM音乐生成请求。
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

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.music_tools import (
            load_music_tools,
        )

        tools = load_music_tools(cfg)
        if not tools:
            raise RuntimeError("BGM音乐生成功能未启用或配置不完整")

        music_tool = tools[0]

        tool_params = {
            "prompt": prompt,
            "style": extract_parameter(request_data, "style", ""),
            "model": extract_parameter(request_data, "model", "V5"),
            "duration": extract_parameter(request_data, "duration", 20),
            "wait": extract_parameter(request_data, "wait", False),
            "max_wait_seconds": extract_parameter(
                request_data, "max_wait_seconds", 600
            ),
            "poll_interval": extract_parameter(request_data, "poll_interval", 5.0),
        }

        with session_context(session_id) as sid:
            result_json = music_tool.func(**tool_params)

        tool_result = json.loads(result_json)

        parts = []
        audio_list = tool_result.get("audio_list", [])
        for audio_url in audio_list:
            parts.append(
                {
                    "content_type": "audio",
                    "content_url": audio_url,
                    "parameter": {
                        "duration": tool_result.get("duration"),
                        "music_style": tool_result.get("style"),
                    },
                }
            )

        # 如果没有 audio_list 但有 error，可能已经在 exception 捕获前抛出，或者在这里处理
        if not parts and tool_result.get("status") == "error":
            raise RuntimeError(tool_result.get("error", "Unknown error"))

        return make_response(
            interface_type="music",
            session_id=sid,
            parts=parts,
            metadata={
                "task_id": tool_result.get("task_id"),
                "model": tool_result.get("model"),
                "audio_count": tool_result.get("audio_count", 0),
            },
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "music",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_music_generation"]
