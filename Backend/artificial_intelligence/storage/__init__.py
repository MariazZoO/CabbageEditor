"""
媒体存储管理模块

提供图片和视频的统一存储管理
"""

from .media_storage import (
    MediaStore,
    StoredImage,
    StoredVideo,
    get_media_store,
    AUTOSAVE_URL_SCHEME,
)

__all__ = [
    "MediaStore",
    "StoredImage",
    "StoredVideo",
    "get_media_store",
    "AUTOSAVE_URL_SCHEME",
]
