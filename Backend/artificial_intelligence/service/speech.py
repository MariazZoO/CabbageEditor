from __future__ import annotations

import json
from typing import Any, Dict

from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
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
        
        # 解析 Tool 返回的 Envelope JSON
        tool_envelope = json.loads(result_json)

        # 检查错误
        if tool_envelope.get("error_code", 0) != 0:
            error_msg = tool_envelope.get("status_info", "未知错误")
            raise RuntimeError(f"语音合成失败: {error_msg}")

        # 提取 llm_content
        llm_content = tool_envelope.get("llm_content", [])
        if not llm_content:
            raise RuntimeError("语音合成未返回有效内容")

        # 提取并清洗 parts
        original_parts = llm_content[0].get("part", [])
        cleaned_parts = []
        for part in original_parts:
            cleaned_part = {
                "content_type": part.get("content_type"),
                "content_url": part.get("content_url"),
                "content_text": part.get("content_text"),
            }
            # 严格过滤 parameter
            if "parameter" in part:
                original_param = part["parameter"]
                cleaned_param = {}
                if "speech_type" in original_param:
                    cleaned_param["speech_type"] = original_param["speech_type"]
                if "duration" in original_param:
                    cleaned_param["duration"] = original_param["duration"]
                if cleaned_param:
                    cleaned_part["parameter"] = cleaned_param
            
            # 移除 None 值字段
            cleaned_part = {k: v for k, v in cleaned_part.items() if v is not None}
            cleaned_parts.append(cleaned_part)

        if not cleaned_parts:
            raise RuntimeError("语音合成未返回有效的音频部分")

        return build_success_response(
            interface_type="speech",
            session_id=session_id,
            metadata=metadata,
            parts=cleaned_parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_error_response(
            interface_type="speech",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_speech_generation"]
