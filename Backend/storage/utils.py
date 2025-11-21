"""
媒体存储工具函数
"""

import mimetypes
import re
import uuid
from pathlib import Path
from threading import RLock
from typing import Optional, Union, TYPE_CHECKING

from config.app_config import get_app_config as get_global_app_config

# autosave 协议前缀（保持本文件内定义，避免额外模块导入）
AUTOSAVE_URL_SCHEME = "autosave://"

# 仅做类型提示，避免循环导入
if TYPE_CHECKING:
    from .models import StoredImage, StoredVideo, StoredAudio

# URL 协议


def resolve_autosave_url(
    root: Path, url: str
) -> Union["StoredImage", "StoredVideo", "StoredAudio", None]:
    """解析 autosave:// URL 并返回对应的媒体元数据"""
    from .models import StoredImage, StoredVideo, StoredAudio

    if not url or not url.startswith(AUTOSAVE_URL_SCHEME):
        return None

    relative = url[len(AUTOSAVE_URL_SCHEME):]
    parts = relative.split("/")

    if len(parts) < 4:
        return None

    session_id, kind, category = parts[0], parts[1], parts[2]
    filename = "/".join(parts[3:])
    path = root / session_id / kind / category / filename

    if not path.exists():
        return None

    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"

    # 判断是视频、音频还是图片
    if category == "video" and kind == "generated":
        return StoredVideo(
            session_id=session_id,
            name=filename,
            mime_type=mime,
            path=path,
            created_at=path.stat().st_mtime,
            kind=kind,
        )
    elif category == "audio" and kind == "generated":
        return StoredAudio(
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


def convert_path_to_autosave_url(root: Path, path_str: Optional[str]) -> Optional[str]:
    """将文件路径转换为 autosave:// URL"""
    if not path_str:
        return None

    try:
        path = Path(path_str).resolve()
        relative = path.relative_to(root.resolve())
        return f"{AUTOSAVE_URL_SCHEME}{relative.as_posix()}"
    except (ValueError, Exception):
        return None


def build_filename(original: str, category: str, mime: str) -> str:
    """构建安全的文件名"""
    stem = Path(original).stem or category
    ext = mime_to_extension(mime)
    token = uuid.uuid4().hex[:8]
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)
    return f"{safe_stem}_{token}{ext}"


def mime_to_extension(mime: str) -> str:
    """将 MIME 类型转换为文件扩展名"""
    if not mime:
        return ".bin"

    # 修正一些常见的非标准或偏好映射
    if mime == "image/jpg":
        return ".jpg"

    # 使用标准库猜测扩展名
    ext = mimetypes.guess_extension(mime)

    if ext:
        # 修正标准库的一些古怪返回
        if ext == ".jpe":
            return ".jpg"
        return ext

    return ".bin"


def category_label(category: str) -> str:
    """获取分类的中文标签"""
    return {"product": "产品", "scene": "场景"}.get(category, category or "图片")


# ============================================================================
# 全局单例
# ============================================================================

_MEDIA_STORE = None
_STORE_LOCK = RLock()


def get_media_store():
    """获取媒体存储管理器单例"""
    # 避免循环导入，延迟导入
    from .manager import MediaStore

    global _MEDIA_STORE
    if _MEDIA_STORE is None:
        with _STORE_LOCK:
            if _MEDIA_STORE is None:
                cfg = get_global_app_config()
                _MEDIA_STORE = MediaStore(cfg.paths.autosave_dir)
    return _MEDIA_STORE
