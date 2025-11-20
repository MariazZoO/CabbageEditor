"""
媒体存储数据模型
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .utils import AUTOSAVE_URL_SCHEME

logger = logging.getLogger(__name__)


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
    def local_url(self) -> str:
        """获取 autosave:// URL"""
        return (
            f"{AUTOSAVE_URL_SCHEME}"
            f"{self.session_id}/{self.kind}/{self.category}/{self.name}"
        )


@dataclass(frozen=True)
class StoredVideo:
    """存储的视频元数据"""

    session_id: str
    name: str
    mime_type: str
    path: Path
    created_at: float
    kind: str
    task_id: Optional[str] = None
    prompt: Optional[str] = None
    source_image_url: Optional[str] = None

    @property
    def file_size_mb(self) -> float:
        """获取文件大小（MB）"""
        try:
            if self.path.exists():
                return self.path.stat().st_size / (1024 * 1024)
        except Exception:
            pass
        return 0.0

    @property
    def local_url(self) -> str:
        """获取 autosave:// URL"""
        return (
            f"{AUTOSAVE_URL_SCHEME}"
            f"{self.session_id}/{self.kind}/video/{self.name}"
        )


@dataclass(frozen=True)
class StoredAudio:
    """存储的音频元数据"""

    session_id: str
    name: str
    mime_type: str
    path: Path
    created_at: float
    kind: str
    task_id: Optional[str] = None
    prompt: Optional[str] = None
    duration: Optional[float] = None

    @property
    def file_size_mb(self) -> float:
        """获取文件大小（MB）"""
        try:
            if self.path.exists():
                return self.path.stat().st_size / (1024 * 1024)
        except Exception:
            pass
        return 0.0

    @property
    def local_url(self) -> str:
        """获取 autosave:// URL"""
        return (
            f"{AUTOSAVE_URL_SCHEME}"
            f"{self.session_id}/{self.kind}/audio/{self.name}"
        )
