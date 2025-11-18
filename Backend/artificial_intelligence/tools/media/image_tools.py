from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

import httpx  # noqa: F401  保留兼容，如后续需要直接请求或错误处理可使用
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.config import AppConfig, MediaToolConfig
from Backend.artificial_intelligence.models.client_image import LingyaImageClient
from Backend.artificial_intelligence.storage import AUTOSAVE_URL_SCHEME, get_media_store
from Backend.artificial_intelligence.tools.session import get_current_session


class ImageGenerationInput(BaseModel):
    prompt: str = Field(..., description="图片生成提示词，描述要生成的图片内容、风格、细节等")
    session_id: str | None = Field(
        default=None,
        description="会话 ID；若省略则自动使用当前聊天会话",
    )
    product_url: str | None = Field(
        default=None,
        description="可选：产品图片的 URL（autosave://...），用于图片合成或编辑。若不提供则使用纯文本生成",
    )
    scene_url: str | None = Field(
        default=None,
        description="可选：场景图片的 URL（autosave://...），用于图片合成或编辑。若不提供则使用纯文本生成",
    )
    use_references: bool = Field(
        default=False,
        description="是否自动使用会话中最近上传的产品和场景图片。设为 True 时会查找最近的上传图片，False 则仅使用明确指定的图片",
    )


def load_image_tools(config: AppConfig) -> List[StructuredTool]:
    image_cfg = config.media.image
    if not _is_media_tool_enabled(image_cfg, config):
        return []

    provider = config.providers[image_cfg.provider]
    client = LingyaImageClient(
        provider=provider,
        model=image_cfg.model,
        base_url=image_cfg.base_url,
    )
    store = get_media_store()

    def _generate(
        prompt: str,
        session_id: str | None = None,
        product_url: str | None = None,
        scene_url: str | None = None,
        use_references: bool = False,
    ) -> str:
        data = ImageGenerationInput(
            prompt=prompt,
            session_id=session_id,
            product_url=product_url,
            scene_url=scene_url,
            use_references=use_references,
        )
        session_id = data.session_id or get_current_session()
        # 只有在明确要求使用引用图片时才自动查找
        if use_references:
            product_url, scene_url = _resolve_reference_urls(
                store=store,
                session_id=session_id,
                explicit_product=data.product_url,
                explicit_scene=data.scene_url,
            )
        else:
            # 仅使用明确指定的图片 URL
            product_url = data.product_url
            scene_url = data.scene_url
        image_b64, mime_type = client.generate(
            prompt=data.prompt,
            store=store,
            product_url=product_url,
            scene_url=scene_url,
        )
        stored = store.save_generated_image(
            session_id=session_id,
            data_base64=f"data:{mime_type};base64,{image_b64}",
            mime_type=mime_type,
        )
        image_url = store.build_image_url(stored)
        payload = {
            "type": "image",
            "prompt": data.prompt,
            "source": provider.name,
            "image_path": str(stored.path),
            "image_name": stored.name,
            "image_url": image_url,
            "session_id": session_id,
        }
        return json.dumps(payload, ensure_ascii=False)

    tool = StructuredTool(
        name="generate_image",
        description=(
            "根据文本提示词生成图片。支持三种模式："
            "1. 纯文本生成：仅提供 prompt 参数，不指定任何图片"
            "2. 图片编辑/合成：提供 prompt 和 product_url/scene_url"
            "3. 自动引用：设置 use_references=True 来使用会话中最近上传的图片"
        ),
        args_schema=ImageGenerationInput,
        func=_generate,
    )
    return [tool]


def _is_media_tool_enabled(cfg: MediaToolConfig, config: AppConfig) -> bool:
    if not cfg.enable:
        return False
    if not cfg.provider or not cfg.model:
        return False
    if cfg.provider not in config.providers:
        return False
    provider = config.providers[cfg.provider]
    return bool(provider.api_key and provider.base_url)


def _resolve_reference_urls(
    *,
    store,
    session_id: str,
    explicit_product: Optional[str],
    explicit_scene: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    product = explicit_product or _latest_upload_url(store, session_id, "product")
    scene = explicit_scene or _latest_upload_url(store, session_id, "scene")
    return product, scene


def _latest_upload_url(store, session_id: str, category: str) -> Optional[str]:
    latest = store.get_latest_upload(session_id, category)
    if latest:
        return store.build_url(latest)
    return None


def _path_from_source(store, source: str) -> Optional[Path]:
    if source.startswith(AUTOSAVE_URL_SCHEME):
        stored = store.resolve_url(source)
        return stored.path if stored else None
    candidate = Path(source)
    return candidate if candidate.exists() else None


__all__ = ["load_image_tools"]
