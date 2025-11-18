from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional, Tuple

import httpx

from Backend.artificial_intelligence.config.config import ProviderConfig
from Backend.artificial_intelligence.storage import AUTOSAVE_URL_SCHEME


class LingyaImageClient:
    """负责与灵雅图片生成/编辑服务交互的客户端。

    根据是否提供参考图片自动选择纯文本生成或编辑接口。
    """

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


def _load_image_base64(store, source: Optional[str]) -> Optional[str]:
    if not source:
        return None
    path = _path_from_source(store, source)
    if not path or not path.exists():
        return None
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _path_from_source(store, source: str):  # 返回 Path 或 None
    if source.startswith(AUTOSAVE_URL_SCHEME):
        stored = store.resolve_url(source)
        return stored.path if stored else None
    from pathlib import Path
    candidate = Path(source)
    return candidate if candidate.exists() else None


__all__ = ["LingyaImageClient"]
