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

    def __init__(
        self, *, provider: ProviderConfig, model: str, base_url: str | None
    ) -> None:
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
        self.headers = {
            **(provider.headers or {}),
            "Authorization": f"Bearer {self.api_key}",
        }

    def generate(
        self,
        *,
        prompt: str,
        aspect_ratio: str,
        store,
        product_url: Optional[str],
        scene_url: Optional[str],
    ) -> Tuple[str, str]:
        """根据可用素材自动选择生成或编辑模式。返回 (image_url, mime_type)"""
        images_data = self._collect_image_data(store, product_url, scene_url)
        if images_data:
            return self._generate_with_images(prompt=prompt, images=images_data)
        return self._generate_from_text(prompt=prompt, aspect_ratio=aspect_ratio)

    def _generate_from_text(self, *, prompt: str, aspect_ratio: str) -> Tuple[str, str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "response_format": "url",  # 明确要求返回URL而不是base64
            "aspect_ratio": aspect_ratio,  # 使用传入的比例参数
        }
        response = httpx.post(
            self.generation_url,
            json=payload,
            headers=self.headers,
            timeout=120,
        )
        response.raise_for_status()
        return self._parse_response(response.json())

    def _generate_with_images(
        self, *, prompt: str, images: List[str]
    ) -> Tuple[str, str]:
        url = self.edit_url.rstrip("/")
        if not url.endswith("/images/edits") and not url.endswith(
            "/images/generations"
        ):
            url = f"{url}/images/generations"  # 图生图也用generations接口
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image": images,
            "response_format": "url",  # 明确要求返回URL
            # 图生图时不支持aspect_ratio设置
        }
        response = httpx.post(url, json=payload, headers=self.headers, timeout=120)
        response.raise_for_status()
        return self._parse_response(response.json())

    def _parse_response(self, body: Dict[str, Any]) -> Tuple[str, str]:
        """解析API响应，返回 (image_url, mime_type)。

        根据API文档，当指定response_format="url"时，API保证返回URL字段。
        """
        images = body.get("data") or []
        if not images:
            raise RuntimeError("Lingya 服务未返回图像数据。")
        item = images[0]

        # API应该返回URL字段（因为我们指定了response_format="url"）
        if "url" in item:
            mime = item.get("mime_type") or "image/png"
            return item["url"], mime

        # 不应该走到这里，如果走到这里说明API行为异常
        raise RuntimeError(
            "API未按预期返回URL字段。请检查response_format参数是否生效。"
        )

    @staticmethod
    def _collect_image_data(
        store,
        product_url: Optional[str],
        scene_url: Optional[str],
    ) -> List[str]:
        """收集图片数据，支持URL或本地路径，返回可用于API的图片数据列表"""
        images: List[str] = []
        for source in (product_url, scene_url):
            if not source:
                continue
            # 如果是HTTP(S) URL，直接使用
            if source.startswith(("http://", "https://")):
                images.append(source)
            # 如果是data URI，直接使用
            elif source.startswith("data:"):
                images.append(source)
            # 如果是本地路径或autosave URL，转换为base64
            else:
                data = _load_image_as_data_uri(store, source)
                if data:
                    images.append(data)
        return images


def _load_image_as_data_uri(store, source: str) -> Optional[str]:
    """将本地图片转换为data URI格式"""
    if not source:
        return None
    path = _path_from_source(store, source)
    if not path or not path.exists():
        return None

    # 读取图片并转换为data URI
    image_bytes = path.read_bytes()
    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    # 根据文件扩展名确定MIME类型
    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/png")

    return f"data:{mime_type};base64,{b64_data}"


def _path_from_source(store, source: str):  # 返回 Path 或 None
    if source.startswith(AUTOSAVE_URL_SCHEME):
        stored = store.resolve_url(source)
        return stored.path if stored else None
    from pathlib import Path

    candidate = Path(source)
    return candidate if candidate.exists() else None


__all__ = ["LingyaImageClient"]
