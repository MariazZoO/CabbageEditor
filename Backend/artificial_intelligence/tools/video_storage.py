"""
视频存储管理模块
扩展 ImageStore 以支持视频文件的保存和管理
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import requests

from Backend.artificial_intelligence.tools.storage import AUTOSAVE_URL_SCHEME


@dataclass(frozen=True)
class StoredVideo:
    """存储的视频元数据"""

    session_id: str
    name: str
    mime_type: str
    path: Path
    created_at: float
    kind: str  # "generated"
    task_id: str | None = None
    prompt: str | None = None
    source_image_url: str | None = None

    @property
    def file_size_mb(self) -> float:
        """获取文件大小（MB）"""
        if self.path.exists():
            return self.path.stat().st_size / (1024 * 1024)
        return 0.0


class VideoStore:
    """
    视频存储管理器

    功能:
    - 下载远程视频文件到本地
    - 管理视频文件的元数据
    - 提供 autosave:// URL 构建和解析
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._videos: dict[str, list[StoredVideo]] = {}

    def download_and_save(
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
        - session_id: 会话 ID
        - video_url: 视频下载 URL
        - task_id: 任务 ID（可选）
        - prompt: 生成提示词（可选）
        - source_image_url: 源图片 URL（可选）
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
            if session_id not in self._videos:
                self._videos[session_id] = []
            self._videos[session_id].append(stored)

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

    def build_url(self, stored: StoredVideo) -> str:
        """
        构建 autosave:// URL

        格式: autosave://{session_id}/generated/video/{filename}
        """
        return (
            f"{AUTOSAVE_URL_SCHEME}"
            f"{stored.session_id}/{stored.kind}/video/{stored.name}"
        )

    def resolve_url(self, url: str) -> Optional[StoredVideo]:
        """
        解析 autosave:// URL 并返回视频元数据

        参数:
        - url: autosave:// URL

        返回:
        - StoredVideo 或 None（如果不存在）
        """
        if not url or not url.startswith(AUTOSAVE_URL_SCHEME):
            return None

        relative = url[len(AUTOSAVE_URL_SCHEME):]
        parts = relative.split("/")

        if len(parts) < 4:
            return None

        session_id, kind, category, filename = (
            parts[0],
            parts[1],
            parts[2],
            "/".join(parts[3:]),
        )

        if kind != "generated" or category != "video":
            return None

        path = self.root / session_id / kind / category / filename

        if not path.exists():
            return None

        # 构建元数据
        return StoredVideo(
            session_id=session_id,
            name=filename,
            mime_type="video/mp4",
            path=path,
            created_at=path.stat().st_mtime,
            kind=kind,
        )

    def list_videos(self, session_id: str) -> list[StoredVideo]:
        """
        列出会话中的所有视频

        参数:
        - session_id: 会话 ID

        返回:
        - 视频列表
        """
        return list(self._videos.get(session_id, []))


# 全局单例
_VIDEO_STORE: Optional[VideoStore] = None


def get_video_store() -> VideoStore:
    """获取视频存储管理器单例"""
    global _VIDEO_STORE
    if _VIDEO_STORE is None:
        from Backend.artificial_intelligence.config.config import get_app_config

        cfg = get_app_config()
        _VIDEO_STORE = VideoStore(cfg.paths.autosave_dir)
    return _VIDEO_STORE


__all__ = ["VideoStore", "StoredVideo", "get_video_store"]
