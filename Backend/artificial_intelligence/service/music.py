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


def handle_music_generation(payload: Any) -> str:
    """
    处理独立的BGM音乐生成请求。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        require_fields(request_data, ["prompt"])

        session_id = request_data.get("session_id")
        prompt = request_data.get("prompt")

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
            "style": request_data.get("style", ""),
            "model": request_data.get("model", "V5"),
            "duration": request_data.get("duration", 20),
            "wait": request_data.get("wait", False),
            "max_wait_seconds": request_data.get("max_wait_seconds", 600),
            "poll_interval": request_data.get("poll_interval", 5.0),
        }

        with session_context(session_id) as sid:
            result_json = music_tool.func(**tool_params)

        tool_result = json.loads(result_json)

        return make_response(
            response_type="music_generation",
            status=tool_result.get("status", "success"),
            session_id=sid,
            task_id=tool_result.get("task_id"),
            model=tool_result.get("model"),
            prompt=tool_result.get("prompt"),
            style=tool_result.get("style"),
            audio_list=tool_result.get("audio_list", []),
            audio_count=tool_result.get("audio_count", 0),
            error=tool_result.get("error"),
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "music_generation",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_music_generation"]
