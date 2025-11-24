"""
媒体存储工具函数
"""

import mimetypes
from threading import RLock
from typing import TYPE_CHECKING
from config.app_config import get_app_config as get_global_app_config

if TYPE_CHECKING:
    pass


# 该模块专注于路径/扩展名工具，历史上的 autosave 解析逻辑已移除


def mime_to_extension(mime: str) -> str:
    if not mime:
        return ".bin"
    if mime == "image/jpg":
        return ".jpg"
    # 显式处理常见的音视频和图片 MIME，避免 guess_extension 返回不理想的结果
    lower = mime.lower()
    explicit_map = {
        # images
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        # videos
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/x-matroska": ".mkv",
        # audio
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
        "audio/webm": ".weba",
        "audio/flac": ".flac",
    }
    if lower in explicit_map:
        return explicit_map[lower]

    ext = mimetypes.guess_extension(mime)
    if ext:
        if ext == ".jpe":
            return ".jpg"
        return ext
    return ".bin"


_MEDIA_STORE = None
_STORE_LOCK = RLock()


def get_media_store():
    from .manager import MediaStore

    global _MEDIA_STORE
    if _MEDIA_STORE is None:
        with _STORE_LOCK:
            if _MEDIA_STORE is None:
                cfg = get_global_app_config()
                _MEDIA_STORE = MediaStore(cfg.paths.autosave_dir)
    return _MEDIA_STORE
