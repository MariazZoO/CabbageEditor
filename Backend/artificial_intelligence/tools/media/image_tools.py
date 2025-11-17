from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.config import AppConfig, MediaToolConfig, ProviderConfig
from Backend.artificial_intelligence.tools.storage import AUTOSAVE_URL_SCHEME, get_image_store
from Backend.artificial_intelligence.tools.session import get_current_session


class ImageGenerationInput(BaseModel):
    prompt: str = Field(..., description="生成指令，需说明产品和场景效果")
    session_id: str | None = Field(
        default=None,
        description="会话 ID；若省略则自动使用当前聊天会话",
    )
    product_url: str | None = Field(
        default=None,
        description="产品图片的 URL（autosave://...），若缺省则使用最近上传的产品图",
    )
    scene_url: str | None = Field(
        default=None,
        description="场景图片的 URL（autosave://...），若缺省则使用最近上传的场景图",
    )


def load_image_tools(config: AppConfig) -> List[StructuredTool]:
    image_cfg = config.media.image
    if not _is_media_tool_enabled(image_cfg, config):
        return []

    provider = config.providers[image_cfg.provider]
    client = _LingyaImageClient(
        provider=provider,
        model=image_cfg.model,
        base_url=image_cfg.base_url,
    )
    store = get_image_store()

    def _generate(
        prompt: str,
        session_id: str | None = None,
        product_url: str | None = None,
        scene_url: str | None = None,
    ) -> str:
        data = ImageGenerationInput(
            prompt=prompt,
            session_id=session_id,
            product_url=product_url,
            scene_url=scene_url,
        )
        session_id = data.session_id or get_current_session()
        product_url, scene_url = _resolve_reference_urls(
            store=store,
            session_id=session_id,
            explicit_product=data.product_url,
            explicit_scene=data.scene_url,
        )
        image_b64, mime_type = client.generate(
            prompt=data.prompt,
            store=store,
            product_url=product_url,
            scene_url=scene_url,
        )
        stored = store.save_generated(
            session_id=session_id,
            data_base64=f"data:{mime_type};base64,{image_b64}",
            mime_type=mime_type,
        )
        image_url = store.build_url(stored)
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
        description="根据文字描述生成图片。支持纯文本生成，也可选择性引用已上传的产品或场景图片进行合成。",
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


class _LingyaImageClient:
    def __init__(self, *, provider: ProviderConfig, model: str, base_url: str | None) -> None:
        if not provider.api_key:
            raise RuntimeError(f"Provider '{provider.name}' 缺少 API Key。")
        self.model = model
        generation_base = base_url or provider.base_url
        if not generation_base:
            raise RuntimeError(f"Provider '{provider.name}' 缺少 base_url。")
        self.generation_url = generation_base.rstrip("/")
        configured_base = base_url.rstrip("/") if base_url else None
        if configured_base and configured_base.endswith("/images/generations"):
            self.edit_url = self.generation_url
        else:
            fallback = provider.base_url or self.generation_url
            self.edit_url = fallback.rstrip("/") if fallback else self.generation_url
        self.api_key = provider.api_key
        self.headers = {**(provider.headers or {}), "Authorization": f"Bearer {self.api_key}"}

    def generate(
        self,
        *,
        prompt: str,
        store,
        product_url: Optional[str],
        scene_url: Optional[str],
    ) -> Tuple[str, str]:
        """根据可用素材自动选择生成或编辑模式。"""
        images_b64 = self._collect_image_b64(store, product_url, scene_url)
        if images_b64:
            return self._generate_with_images(prompt=prompt, images=images_b64)
        return self._generate_from_text(prompt=prompt)

    def _generate_from_text(self, *, prompt: str) -> Tuple[str, str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
        }
        response = httpx.post(
            self.generation_url,
            json=payload,
            headers=self.headers,
            timeout=120,
        )
        response.raise_for_status()
        return self._parse_response(response.json())

    def _generate_with_images(self, *, prompt: str, images: List[str]) -> Tuple[str, str]:
        url = self.edit_url.rstrip("/")
        if not url.endswith("/images/edits") and not url.endswith("/images/generations"):
            url = f"{url}/images/edits"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image": images,
        }
        response = httpx.post(url, json=payload, headers=self.headers, timeout=120)
        response.raise_for_status()
        return self._parse_response(response.json())

    def _parse_response(self, body: Dict[str, Any]) -> Tuple[str, str]:
        images = body.get("data") or []
        if not images:
            raise RuntimeError("Lingya 服务未返回图像数据。")
        item = images[0]
        if "b64_json" in item:
            return item["b64_json"], item.get("mime_type") or "image/png"
        if "url" in item:
            image_resp = httpx.get(item["url"], timeout=120)
            image_resp.raise_for_status()
            mime = image_resp.headers.get("content-type", "image/png")
            return base64.b64encode(image_resp.content).decode("utf-8"), mime
        raise RuntimeError("Lingya 图像响应格式不受支持。")

    @staticmethod
    def _collect_image_b64(
        store,
        product_url: Optional[str],
        scene_url: Optional[str],
    ) -> List[str]:
        images: List[str] = []
        for source in (product_url, scene_url):
            data = _load_image_base64(store, source)
            if data:
                images.append(data)
        return images


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


def _load_image_base64(store, source: Optional[str]) -> Optional[str]:
    if not source:
        return None
    path = _path_from_source(store, source)
    if not path or not path.exists():
        return None
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _path_from_source(store, source: str) -> Optional[Path]:
    if source.startswith(AUTOSAVE_URL_SCHEME):
        stored = store.resolve_url(source)
        return stored.path if stored else None
    candidate = Path(source)
    return candidate if candidate.exists() else None


__all__ = ["load_image_tools"]
