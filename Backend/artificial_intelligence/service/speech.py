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


def handle_speech_generation(payload: Any) -> str:
    """
    处理独立的TTS语音合成请求。
    """
    request_data: Dict[str, Any] = ensure_dict(payload)
    try:
        session_id = request_data.get("session_id")

        # 提取 text
        text = ""
        user_content = extract_latest_user_content(request_data)
        if user_content:
            for part in user_content.get("part", []):
                if part.get("content_type") == "text":
                    text = part.get("content_text", "")
                    break

        if not text:
            text = extract_parameter(request_data, "text")

        if not text:
            raise ValueError("缺少必需参数: text")

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.speech_tools import (
            load_speech_tools,
        )

        tools = load_speech_tools(cfg)
        if not tools:
            raise RuntimeError("TTS语音合成功能未启用或配置不完整")

        tts_tool = tools[0]

        tool_params = {
            "text": text,
            "voice_type": extract_parameter(
                request_data, "voice_type", "zh_female_cancan_mars_bigtts"
            ),
            "speed_ratio": extract_parameter(request_data, "speed_ratio", 1.0),
            "loudness_ratio": extract_parameter(request_data, "loudness_ratio", 1.0),
            "encoding": extract_parameter(request_data, "encoding", "mp3"),
            "rate": extract_parameter(request_data, "rate", 24000),
            "max_wait_seconds": extract_parameter(request_data, "max_wait_seconds", 60),
            "poll_interval": extract_parameter(request_data, "poll_interval", 2.0),
        }

        with session_context(session_id) as sid:
            result_json = tts_tool.func(**tool_params)

        tool_result = json.loads(result_json)

        parts = []
        if tool_result.get("audio_url"):
            # 仅保留 API 文档定义的参数
            speech_params = {}
            if tool_result.get("duration"):
                speech_params["duration"] = tool_result.get("duration")
            if tool_result.get("voice_type"):
                speech_params["speech_type"] = tool_result.get("voice_type")

            parts.append(
                {
                    "content_type": "audio",
                    "content_url": tool_result.get("audio_url"),
                    "url_expire_time": tool_result.get("url_expire_time"),
                    "parameter": speech_params,
                }
            )

        metadata = request_data.get("metadata", {})

        return make_response(
            interface_type="speech",
            session_id=sid,
            parts=parts,
            metadata=metadata,
        )

    except Exception as exc:  # noqa: BLE001
        return make_error(
            "speech",
            request_data.get("session_id"),
            exc,
        )


__all__ = ["handle_speech_generation"]
