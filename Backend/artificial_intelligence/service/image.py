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


def _extract_prompt_from_llm_content(data: Dict[str, Any]) -> str:
    llm_content = data.get("llm_content")
    if not isinstance(llm_content, list) or not llm_content:
        return ""
    first = llm_content[0]
    parts = first.get("part", [])
    prompt = "".join(
        p.get("content_text", "") for p in parts if p.get("content_type") == "text"
    ).strip()
    return prompt


def _extract_images(request_data: Dict[str, Any]) -> Dict[str, str | None]:
    """从 llm_content 中提取图片 URL。

    规则：
    1. 遍历 llm_content[0]["part"] 中的所有 image 类型 part。
    2. 如果 part 的 content_text 包含分类关键词（product/scene），则归类。
    3. 剩余未归类的图片按顺序填充：第一个为 product_url，第二个为 scene_url。
    """
    llm_content = request_data.get("llm_content", [])
    if not isinstance(llm_content, list) or not llm_content:
        return {"product_url": None, "scene_url": None}

    parts = llm_content[0].get("part", [])
    image_parts = [p for p in parts if p.get("content_type") == "image"]

    product_url = None
    scene_url = None
    remaining_parts = []

    # 第一轮：根据 content_text 分类
    for part in image_parts:
        text = part.get("content_text", "").lower()
        url = part.get("content_url")
        if not url:
            continue

        if "product" in text or "产品" in text:
            if not product_url:
                product_url = url
            else:
                # 如果已有 product_url，多余的放入 remaining
                remaining_parts.append(url)
        elif "scene" in text or "场景" in text or "背景" in text:
            if not scene_url:
                scene_url = url
            else:
                remaining_parts.append(url)
        else:
            remaining_parts.append(url)

    # 第二轮：按默认顺序填充空缺
    for url in remaining_parts:
        if not product_url:
            product_url = url
        elif not scene_url:
            scene_url = url
        else:
            break

    return {"product_url": product_url, "scene_url": scene_url}


def handle_image_generation(payload: Any) -> str:
    """图像生成，返回三层结构。"""
    request_data: Dict[str, Any] = ensure_dict(payload)
    session_id = request_data.get("session_id") or "default"
    metadata = request_data.get("metadata", {})
    try:
        prompt = _extract_prompt_from_llm_content(request_data)
        if not prompt:
            raise ValueError("缺少图像生成的 prompt")

        cfg = get_ai_config()
        from Backend.artificial_intelligence.tools.media.image_tools import (
            load_image_tools,
        )

        tools = load_image_tools(cfg)
        if not tools:
            raise RuntimeError("图像生成功能未启用或配置不完整")

        image_tool = tools[0]

        # 提取图片 URL (禁止使用 parameter)
        images = _extract_images(request_data)
        product_url = images["product_url"]
        scene_url = images["scene_url"]

        # 提取参数：图生图时忽略 aspect_ratio
        aspect_ratio = "1:1"
        if not product_url and not scene_url:
            # 仅文生图时使用 aspect_ratio
            aspect_ratio = extract_parameter(request_data, "aspect_ratio", "1:1")
            # 兼容 resolution 参数
            if not aspect_ratio or aspect_ratio == "1:1":
                res = extract_parameter(request_data, "resolution")
                if res:
                    aspect_ratio = res

        with session_context(session_id) as sid:
            result_json = image_tool.func(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                product_url=product_url,
                scene_url=scene_url,
            )
            session_id = sid  # 使用实际上下文 session

        # 解析 Tool 返回的 Envelope JSON
        tool_envelope = parse_tool_response(result_json)

        # 检查错误
        if tool_envelope.get("error_code", 0) != 0:
            error_msg = tool_envelope.get("status_info", "未知错误")
            raise RuntimeError(f"图像生成失败: {error_msg}")

        # 提取 llm_content
        llm_content = tool_envelope.get("llm_content", [])
        if not llm_content:
            raise RuntimeError("图像生成未返回有效内容")

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
                if cleaned_param:
                    cleaned_part["parameter"] = cleaned_param

            # 移除 None 值字段
            cleaned_part = {k: v for k, v in cleaned_part.items() if v is not None}
            cleaned_parts.append(cleaned_part)

        if not cleaned_parts:
            raise RuntimeError("图像生成未返回有效的图片部分")

        return build_success_response(
            interface_type="image",
            session_id=session_id,
            metadata=metadata,
            parts=cleaned_parts,
        )
    except Exception as exc:  # noqa: BLE001
        return build_error_response(
            interface_type="image",
            session_id=session_id,
            metadata=metadata,
            exc=exc,
        )


__all__ = ["handle_image_generation"]
