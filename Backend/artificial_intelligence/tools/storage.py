from __future__ import annotations

import base64
import mimetypes
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Dict, Optional, Tuple

from Backend.artificial_intelligence.config.config import get_app_config

_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.IGNORECASE)


AUTOSAVE_URL_SCHEME = "autosave://"


@dataclass(frozen=True)
class StoredImage:
    session_id: str
    category: str
    name: str
    mime_type: str
    path: Path
    created_at: float
    kind: str

    @property
    def data_url(self) -> str:
        b64 = base64.b64encode(self.path.read_bytes()).decode("utf-8")
        return f"data:{self.mime_type};base64,{b64}"


class ImageStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._uploads: Dict[str, Dict[str, StoredImage]] = {}
        self._generated: Dict[str, list[StoredImage]] = {}

    def save_upload(
        self,
        *,
        session_id: str,
        data: str,
        category: str,
        original_name: str,
    ) -> StoredImage:
        mime, payload = _split_base64(data)
        filename = _build_filename(original_name, category, mime)
        path = self._write_file(session_id, "uploads", category, filename, payload)
        stored = StoredImage(
            session_id=session_id,
            category=category,
            name=filename,
            mime_type=mime,
            path=path,
            created_at=time.time(),
            kind="uploads",
        )
        with self._lock:
            self._uploads.setdefault(session_id, {})[category] = stored
        return stored

    def save_generated(
        self,
        *,
        session_id: str,
        data_base64: str,
        mime_type: str = "image/png",
        prefix: str = "generated",
    ) -> StoredImage:
        _, payload = _split_base64(data_base64, assume_mime=mime_type)
        filename = _build_filename(f"{prefix}-{uuid.uuid4().hex}", prefix, mime_type)
        path = self._write_file(session_id, "generated", prefix, filename, payload)
        stored = StoredImage(
            session_id=session_id,
            category="generated",
            name=filename,
            mime_type=mime_type,
            path=path,
            created_at=time.time(),
            kind="generated",
        )
        with self._lock:
            self._generated.setdefault(session_id, []).append(stored)
        return stored

    def get_latest_upload(
        self, session_id: str, category: str
    ) -> Optional[StoredImage]:
        with self._lock:
            return self._uploads.get(session_id, {}).get(category)

    def get_latest_pair(
        self, session_id: str
    ) -> Tuple[Optional[StoredImage], Optional[StoredImage]]:
        with self._lock:
            uploads = self._uploads.get(session_id, {})
            return uploads.get("product"), uploads.get("scene")

    def list_generated(self, session_id: str) -> list[StoredImage]:
        with self._lock:
            return list(self._generated.get(session_id, []))

    def register_reference(
        self, session_id: str, category: str, stored: StoredImage
    ) -> None:
        with self._lock:
            self._uploads.setdefault(session_id, {})[category] = stored

    def build_url(self, stored: StoredImage) -> str:
        return (
            f"{AUTOSAVE_URL_SCHEME}"
            f"{stored.session_id}/{stored.kind}/{stored.category}/{stored.name}"
        )

    def resolve_url(self, url: str) -> Optional[StoredImage]:
        if not url or not url.startswith(AUTOSAVE_URL_SCHEME):
            return None
        relative = url[len(AUTOSAVE_URL_SCHEME):]
        parts = relative.split("/")
        if len(parts) < 4:
            return None
        session_id, kind, category = parts[0], parts[1], parts[2]
        filename = "/".join(parts[3:])
        path = self.root / session_id / kind / category / filename
        if not path.exists():
            return None
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        return StoredImage(
            session_id=session_id,
            category=category,
            name=filename,
            mime_type=mime,
            path=path,
            created_at=path.stat().st_mtime,
            kind=kind,
        )

    def _write_file(
        self,
        session_id: str,
        section: str,
        category: str,
        filename: str,
        payload_base64: str,
    ) -> Path:
        session_dir = self.root / session_id / section / category
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / filename
        path.write_bytes(base64.b64decode(payload_base64))
        return path


def _split_base64(data: str, *, assume_mime: Optional[str] = None) -> Tuple[str, str]:
    stripped = data.strip()
    match = _DATA_URL_RE.match(stripped)
    if match:
        return match.group("mime") or assume_mime or "image/png", match.group("data")
    if assume_mime is None:
        assume_mime = "image/png"
    return assume_mime, stripped


def _build_filename(original: str, category: str, mime: str) -> str:
    stem = Path(original).stem or category
    ext = _mime_to_extension(mime)
    token = uuid.uuid4().hex[:8]
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)
    return f"{safe_stem}_{token}{ext}"


def _mime_to_extension(mime: str) -> str:
    lower = mime.lower()
    # 先移除参数部分（如"; charset=utf-8"）
    base_mime = lower.split(";")[0].strip()

    # 常见的图片格式映射
    mime_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "image/bmp": ".bmp",
        "image/x-bmp": ".bmp",
        "image/x-ms-bmp": ".bmp",
        "image/x-windows-bmp": ".bmp",
        "image/tiff": ".tiff",
        "image/x-tiff": ".tiff",
        "image/svg+xml": ".svg",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico",
        "image/x-jfif": ".jpg",
        "image/x-portable-bitmap": ".pbm",
        "image/x-portable-graymap": ".pgm",
        "image/x-portable-pixmap": ".ppm",
        "image/x-rgb": ".rgb",
        "image/x-xbitmap": ".xbm",
        "image/x-xpixmap": ".xpm",
    }

    # 首先尝试直接映射
    if base_mime in mime_map:
        return mime_map[base_mime]

    # 如果MIME类型以image/开头但不在映射表中，尝试从MIME类型名提取扩展名
    if base_mime.startswith("image/"):
        subtype = base_mime.split("/", 1)[1].split("+")[0].strip()
        # 移除非法字符
        ext = re.sub(r"[^a-z0-9]", "", subtype)
        if ext:
            # 处理jpeg/jpg同义词
            if ext == "jpeg":
                return ".jpg"
            return f".{ext}"

    # 默认返回png
    return ".png"


_IMAGE_STORE: Optional[ImageStore] = None
_STORE_LOCK = RLock()


def get_image_store() -> ImageStore:
    global _IMAGE_STORE
    if _IMAGE_STORE is None:
        with _STORE_LOCK:
            if _IMAGE_STORE is None:
                cfg = get_app_config()
                _IMAGE_STORE = ImageStore(cfg.paths.autosave_dir)
    return _IMAGE_STORE


__all__ = ["get_image_store", "ImageStore", "StoredImage", "AUTOSAVE_URL_SCHEME"]
