"""
媒体存储管理模块

提供图片、视频和音频的统一存储管理
"""

from .manager import MediaStore
from .models import StoredImage, StoredVideo, StoredAudio
from .utils import AUTOSAVE_URL_SCHEME, get_media_store

__all__ = [
    "MediaStore",
    "StoredImage",
    "StoredVideo",
    "StoredAudio",
    "get_media_store",
    "AUTOSAVE_URL_SCHEME",
]
