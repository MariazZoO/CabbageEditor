from __future__ import annotations

from typing import Any, Dict

from Backend.artificial_intelligence.config.ai_config import get_ai_config

from Backend.artificial_intelligence.service.common import (
    ensure_dict,
    build_error_response,
    build_success_response,
    session_context,
    extract_parameter,
    parse_tool_response,
)


def _extract_prompt_and_image(request_data: Dict[str, Any]) -> Dict[str, str]:
    llm_content = request_data.get("llm_content", [])
    prompt = ""
    image_url = ""
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
            session_id = sid

        # 解析 Tool 返回的 Envelope JSON
        tool_envelope = parse_tool_response(result_json)

        # 检查错误
        if tool_envelope.get("error_code", 0) != 0:
            error_msg = tool_envelope.get("status_info", "未知错误")
            raise RuntimeError(f"视频生成失败: {error_msg}")

        # 提取 llm_content
        llm_content = tool_envelope.get("llm_content", [])
        if not llm_content:
            raise RuntimeError("视频生成未返回有效内容")

        # 提取并清洗 parts
        original_parts = llm_content[0].get("part", [])
        cleaned_parts = []
        for part in original_parts:
            cleaned_part = {
                "content_type": part.get("content_type"),
                "content_url": part.get("content_url"),
                "content_text": part.get("content_text", ""),
            }
            # 严格过滤 parameter
            if "parameter" in part:
                original_param = part["parameter"]
                cleaned_param = {}
                if "resolution" in original_param:
                    cleaned_param["resolution"] = original_param["resolution"]
                if "duration" in original_param:
                    cleaned_param["duration"] = original_param["duration"]
                if cleaned_param:
                    cleaned_part["parameter"] = cleaned_param

            # 移除 None 值字段
            cleaned_part = {k: v for k, v in cleaned_part.items() if v is not None}
            cleaned_parts.append(cleaned_part)

        if not cleaned_parts:
            raise RuntimeError("视频生成未返回有效的视频部分")

        return build_success_response(
            interface_type="video",
            session_id=session_id,
            metadata=metadata,
            parts=cleaned_parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_error_response(
            interface_type="video",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_video_generation"]
