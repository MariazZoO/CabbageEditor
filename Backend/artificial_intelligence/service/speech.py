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


def handle_speech_generation(payload: Any) -> str:
    """
    处理独立的TTS语音合成请求。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        require_fields(request_data, ["text"])

        session_id = request_data.get("session_id")
        text = request_data.get("text")

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.speech_tools import (
            load_tts_tools,
        )

        tools = load_tts_tools(cfg)
        if not tools:
            raise RuntimeError("TTS语音合成功能未启用或配置不完整")

        tts_tool = tools[0]

        tool_params = {
            "text": text,
            "voice_type": request_data.get(
                "voice_type", "zh_female_cancan_mars_bigtts"
            ),
            "speed_ratio": request_data.get("speed_ratio", 1.0),
            "loudness_ratio": request_data.get("loudness_ratio", 1.0),
            "encoding": request_data.get("encoding", "mp3"),
            "rate": request_data.get("rate", 24000),
            "max_wait_seconds": request_data.get("max_wait_seconds", 60),
            "poll_interval": request_data.get("poll_interval", 2.0),
        }

        with session_context(session_id) as sid:
            result_json = tts_tool.func(**tool_params)

        tool_result = json.loads(result_json)

        return make_response(
            response_type="tts_generation",
            status=tool_result.get("status", "success"),
            session_id=sid,
            task_id=tool_result.get("task_id"),
            audio_url=tool_result.get("audio_url"),
            duration=tool_result.get("duration"),
            req_text_length=tool_result.get("req_text_length"),
            url_expire_time=tool_result.get("url_expire_time"),
            encoding=tool_result.get("encoding"),
            voice_type=tool_result.get("voice_type"),
            error=tool_result.get("error"),
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "tts_generation",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_speech_generation"]
