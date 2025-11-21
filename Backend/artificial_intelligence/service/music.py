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
        tool_result = json.loads(result_json)

        # 检查工具返回的业务错误
        if "error" in tool_result and tool_result["error"]:
            raise RuntimeError(f"音乐生成失败: {tool_result['error']}")
        tool_status = tool_result.get("status", "")
        if tool_status in ["failed", "error"]:
            error_msg = tool_result.get("error", "未知错误")
            raise RuntimeError(f"音乐生成失败: {error_msg}")

        audio_list = tool_result.get("audio_list", [])
        if not audio_list:
            raise RuntimeError("音乐生成未返回任何音频")

        parts = [
            {
                "content_type": "audio",
                "content_url": audio_list[0] if audio_list else "",
                "parameter": {
                    "music_style": tool_result.get("style"),
                    "duration": request_data.get("duration", 20),
                    "audio_count": len(audio_list),
                },  # 过滤 model
            }
        ]
        return build_multilayer_success(
            interface_type="music",
            session_id=session_id,
            metadata=metadata,
            parts=parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_multilayer_error(
            interface_type="music",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_music_generation"]
