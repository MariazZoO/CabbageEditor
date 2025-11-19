"""
统一的媒体存储管理模块

支持图片和视频的保存、管理和URL解析
"""

from __future__ import annotations

import base64
import mimetypes
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Optional

import requests

from Backend.artificial_intelligence.config.config import get_app_config

# URL 协议
AUTOSAVE_URL_SCHEME = "autosave://"

# Base64 数据URL正则
_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.IGNORECASE)


@dataclass(frozen=True)
class StoredImage:
    """存储的图片元数据"""

    session_id: str
    category: str
    name: str
    mime_type: str
    path: Path
    created_at: float
    kind: str

    @property
    def data_url(self) -> str:
        """
        获取 Base64 编码的数据 URL

        注意：此方法每次调用都会读取文件。
        对于频繁访问，建议使用 MediaStore.get_cached_data_url()
        """
        b64 = base64.b64encode(self.path.read_bytes()).decode("utf-8")
        return f"data:{self.mime_type};base64,{b64}"

    @property
    def cache_key(self) -> str:
        """获取缓存键（用于缓存 data_url）"""
        return f"{self.session_id}/{self.kind}/{self.category}/{self.name}"


@dataclass(frozen=True)
class StoredVideo:
    """存储的视频元数据"""

    session_id: str
    name: str
    mime_type: str
    path: Path
    created_at: float
    kind: str
    task_id: str | None = None
    prompt: str | None = None
    source_image_url: str | None = None

    @property
    def file_size_mb(self) -> float:
        """获取文件大小（MB）"""
        if self.path.exists():
            return self.path.stat().st_size / (1024 * 1024)
        return 0.0


class MediaStore:
    """
    统一的媒体存储管理器

    功能：
    - 图片上传和生成图片的保存
    - 视频文件的下载和保存
    - autosave:// URL 的构建和解析
    - 媒体文件的查询和管理
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

        # 图片存储索引
        self._uploads: dict[str, dict[str, StoredImage]] = {}
        self._generated_images: dict[str, list[StoredImage]] = {}

        # 视频存储索引
        self._videos: dict[str, list[StoredVideo]] = {}

        # Data URL 缓存（避免重复读取和编码文件）
        self._data_url_cache: dict[str, str] = {}

    # ========================================================================
    # 图片相关方法
    # ========================================================================

    def save_upload(
        self,
        *,
        session_id: str,
        data: str,
        category: str,
        original_name: str,
    ) -> StoredImage:
        """
        保存上传的图片

        参数:
        - session_id: 会话ID
        - data: Base64 编码的图片数据
        - category: 分类（如 "product", "scene"）
        - original_name: 原始文件名

        返回:
        - StoredImage: 存储的图片元数据
        """
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

    def save_generated_image(
        self,
        *,
        session_id: str,
        data_base64: str,
        mime_type: str = "image/png",
        prefix: str = "generated",
    ) -> StoredImage:
        """
        保存生成的图片

        参数:
        - session_id: 会话ID
        - data_base64: Base64 编码的图片数据
        - mime_type: MIME 类型
        - prefix: 文件名前缀

        返回:
        - StoredImage: 存储的图片元数据
        """
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
            self._generated_images.setdefault(session_id, []).append(stored)

        return stored

    def get_latest_upload(
        self, session_id: str, category: str
    ) -> Optional[StoredImage]:
        """获取最新上传的图片"""
        with self._lock:
            return self._uploads.get(session_id, {}).get(category)

    def get_latest_pair(
        self, session_id: str
    ) -> tuple[Optional[StoredImage], Optional[StoredImage]]:
        """获取最新的产品图和场景图"""
        with self._lock:
            uploads = self._uploads.get(session_id, {})
            return uploads.get("product"), uploads.get("scene")

    def list_generated_images(self, session_id: str) -> list[StoredImage]:
        """列出会话中生成的所有图片"""
        with self._lock:
            return list(self._generated_images.get(session_id, []))

    def register_reference(
        self, session_id: str, category: str, stored: StoredImage
    ) -> None:
        """注册引用图片"""
        with self._lock:
            self._uploads.setdefault(session_id, {})[category] = stored

    # ========================================================================
    # 视频相关方法
    # ========================================================================

    def download_and_save_video(
        self,
        *,
        session_id: str,
        video_url: str,
        task_id: str | None = None,
        prompt: str | None = None,
        source_image_url: str | None = None,
        timeout: int = 300,
    ) -> StoredVideo:
        """
        下载远程视频并保存到本地

        参数:
        - session_id: 会话ID
        - video_url: 视频下载URL
        - task_id: 任务ID（可选）
        - prompt: 生成提示词（可选）
        - source_image_url: 源图片URL（可选）
        - timeout: 下载超时时间（秒）

        返回:
        - StoredVideo: 存储的视频元数据
        """
        # 生成文件名
        token = uuid.uuid4().hex[:12]
        filename = f"video_{token}.mp4"

        # 构建保存路径
        video_dir = self.root / session_id / "generated" / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        file_path = video_dir / filename

        # 下载视频
        print("\n📥 正在下载视频...")
        print(f"   保存路径: {file_path}")

        try:
            response = requests.get(video_url, stream=True, timeout=timeout)
            response.raise_for_status()

            # 获取文件总大小
            total_size = int(response.headers.get("content-length", 0))
            block_size = 8192  # 8KB
            downloaded_size = 0

            # 开始下载
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 显示进度
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            downloaded_mb = downloaded_size / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            print(
                                f"\r   进度: {progress:.1f}% "
                                f"({downloaded_mb:.2f}MB / {total_mb:.2f}MB)",
                                end="",
                                flush=True,
                            )

            print()  # 换行

            # 创建视频元数据
            stored = StoredVideo(
                session_id=session_id,
                name=filename,
                mime_type="video/mp4",
                path=file_path,
                created_at=time.time(),
                kind="generated",
                task_id=task_id,
                prompt=prompt,
                source_image_url=source_image_url,
            )

            # 保存到内存索引
            with self._lock:
                self._videos.setdefault(session_id, []).append(stored)

            file_size_mb = stored.file_size_mb
            print("✓ 视频下载完成！")
            print(f"   文件大小: {file_size_mb:.2f} MB")
            print(f"   保存位置: {file_path}")

            return stored

        except Exception as e:
            # 如果下载失败，删除不完整的文件
            if file_path.exists():
                file_path.unlink()
            raise RuntimeError(f"视频下载失败: {e}") from e

    def list_videos(self, session_id: str) -> list[StoredVideo]:
        """列出会话中的所有视频"""
        with self._lock:
            return list(self._videos.get(session_id, []))

    # ========================================================================
    # URL 相关方法
    # ========================================================================

    def build_image_url(self, stored: StoredImage) -> str:
        """
        构建图片的 autosave:// URL

        格式: autosave://{session_id}/{kind}/{category}/{filename}
        """
        return (
            f"{AUTOSAVE_URL_SCHEME}"
            f"{stored.session_id}/{stored.kind}/{stored.category}/{stored.name}"
        )

    def build_video_url(self, stored: StoredVideo) -> str:
        """
        构建视频的 autosave:// URL

        格式: autosave://{session_id}/generated/video/{filename}
        """
        return (
            f"{AUTOSAVE_URL_SCHEME}"
            f"{stored.session_id}/{stored.kind}/video/{stored.name}"
        )

    def resolve_url(self, url: str) -> StoredImage | StoredVideo | None:
        """
        解析 autosave:// URL 并返回对应的媒体元数据

        参数:
        - url: autosave:// URL

        返回:
        - StoredImage、StoredVideo 或 None
        """
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

        mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

        # 判断是视频还是图片
        if category == "video" and kind == "generated":
            return StoredVideo(
                session_id=session_id,
                name=filename,
                mime_type=mime,
                path=path,
                created_at=path.stat().st_mtime,
                kind=kind,
            )
        else:
            return StoredImage(
                session_id=session_id,
                category=category,
                name=filename,
                mime_type=mime,
                path=path,
                created_at=path.stat().st_mtime,
                kind=kind,
            )

    # ========================================================================
    # 内部辅助方法
    # ========================================================================

    def _write_file(
        self,
        session_id: str,
        section: str,
        category: str,
        filename: str,
        payload_base64: str,
    ) -> Path:
        """写入文件到磁盘"""
        session_dir = self.root / session_id / section / category
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / filename
        path.write_bytes(base64.b64decode(payload_base64))
        return path

    # ========================================================================
    # 图片处理辅助方法（从 image_handler.py 迁移）
    # ========================================================================

    def register_uploads(self, request) -> list[str]:
        """
        注册用户上传的图片到会话

        参数:
        - request: IncomingRequest 对象

        返回:
        - 上传说明列表
        """
        notes: list[str] = []
        for attachment in request.images:
            stored = None
            if attachment.data:
                stored = self.save_upload(
                    session_id=request.session_id,
                    data=attachment.data,
                    category=attachment.category,
                    original_name=attachment.name,
                )
            elif attachment.url:
                stored = self.resolve_url(attachment.url)
                if (
                    stored
                    and isinstance(stored, StoredImage)
                    and stored.session_id != request.session_id
                ):
                    stored = self.clone_image_to_session(
                        stored, request.session_id, attachment.category
                    )

            if stored and isinstance(stored, StoredImage):
                self.register_reference(request.session_id, attachment.category, stored)
                url = self.build_image_url(stored)
                notes.append(f"已上传{_category_label(attachment.category)}图片：{url}")
            elif attachment.url:
                notes.append(
                    f"引用{_category_label(attachment.category)}图片：{attachment.url}"
                )

        return notes

    def get_cached_data_url(self, stored: StoredImage) -> str:
        """
        获取图片的 Base64 数据 URL（带缓存）

        参数:
        - stored: 图片元数据

        返回:
        - data:image/xxx;base64,... 格式的字符串

        注意：
        - 首次访问会读取文件并缓存
        - 后续访问直接返回缓存
        - 线程安全
        """
        cache_key = stored.cache_key

        with self._lock:
            # 检查缓存
            if cache_key in self._data_url_cache:
                return self._data_url_cache[cache_key]

            # 生成 data URL
            data_url = stored.data_url

            # 缓存结果
            self._data_url_cache[cache_key] = data_url

            return data_url

    def clear_data_url_cache(self, stored: StoredImage | None = None) -> None:
        """
        清除 data URL 缓存

        参数:
        - stored: 可选，指定要清除的图片。如果为 None，清除所有缓存
        """
        with self._lock:
            if stored is None:
                self._data_url_cache.clear()
            else:
                self._data_url_cache.pop(stored.cache_key, None)

    def load_image_data_url(
        self, path_str: str | None, use_cache: bool = True
    ) -> str | None:
        """
        将图片路径转换为 Base64 数据 URL

        参数:
        - path_str: 文件路径或 autosave:// URL
        - use_cache: 是否使用缓存（默认 True）

        返回:
        - data:image/xxx;base64,... 格式的字符串
        """
        if not path_str:
            return None

        # 如果是 autosave:// URL，尝试使用缓存
        if path_str.startswith(AUTOSAVE_URL_SCHEME):
            stored = self.resolve_url(path_str)
            if stored and isinstance(stored, StoredImage):
                if use_cache:
                    return self.get_cached_data_url(stored)
                else:
                    return stored.data_url
            path = stored.path if stored else None
        else:
            path = Path(path_str)

        if path is None or not path.exists():
            return None

        # 对于非 autosave:// 路径，直接读取（不缓存）
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        return f"data:{mime};base64,{encoded}"

    def path_to_url(self, path_str: str | None) -> str | None:
        """
        将文件路径转换为 autosave:// URL

        参数:
        - path_str: 文件系统路径

        返回:
        - autosave:// URL
        """
        if not path_str:
            return None

        path = Path(path_str).resolve()
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            return None
        return f"{AUTOSAVE_URL_SCHEME}{relative.as_posix()}"

    def clone_image_to_session(
        self, stored: StoredImage | None, session_id: str, category: str
    ) -> StoredImage:
        """
        克隆图片到新会话

        参数:
        - stored: 原始图片
        - session_id: 目标会话ID
        - category: 分类

        返回:
        - 克隆后的图片元数据
        """
        if stored is None:
            raise ValueError("无法克隆不存在的图片")

        # 使用缓存的 data_url 提高性能
        return self.save_upload(
            session_id=session_id,
            data=self.get_cached_data_url(stored),
            category=category or stored.category,
            original_name=stored.name,
        )


# ============================================================================
# 辅助函数
# ============================================================================


def _split_base64(data: str, *, assume_mime: Optional[str] = None) -> tuple[str, str]:
    """
    分离 Base64 数据和 MIME 类型

    返回: (mime_type, base64_payload)
    """
    stripped = data.strip()
    match = _DATA_URL_RE.match(stripped)
    if match:
        return match.group("mime") or assume_mime or "image/png", match.group("data")
    if assume_mime is None:
        assume_mime = "image/png"
    return assume_mime, stripped


def _build_filename(original: str, category: str, mime: str) -> str:
    """构建安全的文件名"""
    stem = Path(original).stem or category
    ext = _mime_to_extension(mime)
    token = uuid.uuid4().hex[:8]
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)
    return f"{safe_stem}_{token}{ext}"


def _mime_to_extension(mime: str) -> str:
    """将 MIME 类型转换为文件扩展名"""
    lower = mime.lower()
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
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
    }

    # 首先尝试直接映射
    if base_mime in mime_map:
        return mime_map[base_mime]

    # 如果MIME类型以image/或video/开头但不在映射表中
    if base_mime.startswith(("image/", "video/")):
        subtype = base_mime.split("/", 1)[1].split("+")[0].strip()
        ext = re.sub(r"[^a-z0-9]", "", subtype)
        if ext:
            if ext == "jpeg":
                return ".jpg"
            return f".{ext}"

    # 默认返回
    if base_mime.startswith("video/"):
        return ".mp4"
    return ".png"


def _category_label(category: str) -> str:
    """获取分类的中文标签"""
    return {"product": "产品", "scene": "场景"}.get(category, category or "图片")


# ============================================================================
# 全局单例
# ============================================================================

_MEDIA_STORE: Optional[MediaStore] = None
_STORE_LOCK = RLock()


def get_media_store() -> MediaStore:
    """获取媒体存储管理器单例"""
    global _MEDIA_STORE
    if _MEDIA_STORE is None:
        with _STORE_LOCK:
            if _MEDIA_STORE is None:
                cfg = get_app_config()
                _MEDIA_STORE = MediaStore(cfg.paths.autosave_dir)
    return _MEDIA_STORE


__all__ = [
    "MediaStore",
    "StoredImage",
    "StoredVideo",
    "get_media_store",
    "AUTOSAVE_URL_SCHEME",
]
