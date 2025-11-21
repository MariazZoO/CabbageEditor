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


def _extract_prompt_and_image(request_data: Dict[str, Any]) -> Dict[str, str]:
    llm_content = request_data.get("llm_content", [])
    prompt = request_data.get("prompt", "")
    image_url = request_data.get("image_url", "")
    if isinstance(llm_content, list) and llm_content:
        parts = llm_content[0].get("part", [])
        prompt_parts = [
            p.get("content_text", "") for p in parts if p.get("content_type") == "text"
        ]
        image_parts = [
            p.get("content_url", "") for p in parts if p.get("content_type") == "image"
        ]
        if prompt_parts:
            prompt = " ".join(prompt_parts).strip()
        if image_parts:
            image_url = image_parts[0]
    return {"prompt": prompt, "image_url": image_url}


def handle_video_generation(payload: Any) -> str:
    """视频生成三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    session_id = request_data.get("session_id") or "default"
    metadata = request_data.get("metadata", {})
    try:
        extracted = _extract_prompt_and_image(request_data)
        prompt = extracted["prompt"]
        image_url = extracted["image_url"]
        if not prompt or not image_url:
            raise ValueError("缺少 prompt 或 image_url")
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
            session_id = sid
        tool_result = json.loads(result_json)

        # 检查工具返回的业务错误
        if "error" in tool_result and tool_result["error"]:
            raise RuntimeError(f"视频生成失败: {tool_result['error']}")
        tool_status = tool_result.get("status", "")
        if tool_status in ["failed", "error"]:
            error_msg = tool_result.get("error", "未知错误")
            raise RuntimeError(f"视频生成失败: {error_msg}")

        video_url = tool_result.get("video_url", "")
        if not video_url and tool_status == "succeeded":
            raise RuntimeError("视频生成成功但未返回有效的 URL")

        parts = [
            {
                "content_type": "video",
                "content_url": video_url,
                "parameter": {
                    "prompt": tool_result.get("prompt", prompt),
                    "resolution": tool_result.get("resolution", resolution),
                    "status": tool_status or "unknown",
                    # 过滤掉 task_id / model 等测试不希望出现的字段
                },
            }
        ]
        return build_multilayer_success(
            interface_type="video",
            session_id=session_id,
            metadata=metadata,
            parts=parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_multilayer_error(
            interface_type="video",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_video_generation"]
