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


def _extract_text(request_data: Dict[str, Any]) -> str:
    if "text" in request_data:
        return request_data.get("text", "")
    llm_content = request_data.get("llm_content")
    if isinstance(llm_content, list) and llm_content:
        parts = llm_content[0].get("part", [])
        txt = "\n".join(
            p.get("content_text", "") for p in parts if p.get("content_type") == "text"
        ).strip()
        return txt
    return ""


def handle_speech_generation(payload: Any) -> str:
    """语音生成三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    metadata = request_data.get("metadata", {})
    session_id = request_data.get("session_id") or "default"
    try:
        text = _extract_text(request_data)
        if not text:
            raise ValueError("缺少待合成的文本")
        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.speech_tools import (
            load_speech_tools,
        )

        tools = load_speech_tools(cfg)
        if not tools:
            raise RuntimeError("TTS语音合成功能未启用或配置不完整")
        speech_tool = tools[0]
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
            result_json = speech_tool.func(**tool_params)
            session_id = sid
        tool_result = json.loads(result_json)

        # 检查工具返回的业务错误
        if "error" in tool_result and tool_result["error"]:
            raise RuntimeError(f"语音合成失败: {tool_result['error']}")
        tool_status = tool_result.get("status", "")
        if tool_status in ["failed", "error"]:
            error_msg = tool_result.get("error", "未知错误")
            raise RuntimeError(f"语音合成失败: {error_msg}")

        audio_url = tool_result.get("audio_url", "")
        if not audio_url:
            raise RuntimeError("语音合成未返回有效的 URL")

        parts = [
            {
                "content_type": "audio",
                "content_url": audio_url,
                "parameter": {
                    "speech_type": tool_result.get("voice_type"),
                    "duration": tool_result.get("duration"),
                },  # 过滤 encoding
            }
        ]
        return build_multilayer_success(
            interface_type="speech",
            session_id=session_id,
            metadata=metadata,
            parts=parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_multilayer_error(
            interface_type="speech",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_speech_generation"]
