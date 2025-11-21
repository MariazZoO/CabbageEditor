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


def _extract_prompt(request_data: Dict[str, Any]) -> str:
    if "prompt" in request_data:
        return request_data.get("prompt", "")
    llm_content = request_data.get("llm_content")
    if isinstance(llm_content, list) and llm_content:
        parts = llm_content[0].get("part", [])
        return "\n".join(
            p.get("content_text", "") for p in parts if p.get("content_type") == "text"
        ).strip()
    return ""


def handle_music_generation(payload: Any) -> str:
    """音乐生成三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    metadata = request_data.get("metadata", {})
    session_id = request_data.get("session_id") or "default"
    try:
        prompt = _extract_prompt(request_data)
        if not prompt:
            raise ValueError("缺少音乐生成的 prompt")
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
            session_id = sid
        
        # 解析 Tool 返回的 Envelope JSON
        tool_envelope = json.loads(result_json)

        # 检查错误
        if tool_envelope.get("error_code", 0) != 0:
            error_msg = tool_envelope.get("status_info", "未知错误")
            raise RuntimeError(f"音乐生成失败: {error_msg}")

        # 提取 llm_content
        llm_content = tool_envelope.get("llm_content", [])
        if not llm_content:
            raise RuntimeError("音乐生成未返回有效内容")

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
                if "music_style" in original_param:
                    cleaned_param["music_style"] = original_param["music_style"]
                if "duration" in original_param:
                    cleaned_param["duration"] = original_param["duration"]
                if cleaned_param:
                    cleaned_part["parameter"] = cleaned_param
            
            # 移除 None 值字段
            cleaned_part = {k: v for k, v in cleaned_part.items() if v is not None}
            cleaned_parts.append(cleaned_part)

        if not cleaned_parts:
            raise RuntimeError("音乐生成未返回有效的音频部分")

        return build_success_response(
            interface_type="music",
            session_id=session_id,
            metadata=metadata,
            parts=cleaned_parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_error_response(
            interface_type="music",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_music_generation"]
