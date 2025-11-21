"""
媒体存储管理器
"""
from __future__ import annotations

import logging
import mimetypes
import time
import uuid
from pathlib import Path
from typing import Optional, Union

from .models import StoredImage, StoredVideo, StoredAudio
from .utils import (
    convert_path_to_autosave_url,
    mime_to_extension,
    resolve_autosave_url,
)
from .downloader import download_file

logger = logging.getLogger(__name__)


class MediaStore:
    """
    统一的媒体存储管理器

    功能：
    - 资源下载和保存 (URL -> 本地文件)
    - autosave:// URL 的构建和解析
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def save_resource_from_url(
        self,
        *,
        session_id: str,
        url: str,
        category: str,
        kind: str = "uploads",
        original_name: Optional[str] = None,
        timeout: int = 300,
    ) -> str:
        """
        从 URL 下载资源并保存，返回本地 autosave URL

        参数:
        - session_id: 会话ID
        - url: 远程资源 URL
        - category: 分类 (product, scene, generated 等)
        - kind: 类型 (uploads, generated)
        - original_name: 原始文件名 (可选，用于推断扩展名)
        - timeout: 下载超时

        返回:
        - autosave://... URL
        """
        # 1. 确定文件名和路径
        # 尝试从 URL 或 original_name 推断扩展名，默认 .bin
        ext = ".bin"
        if original_name:
            ext = Path(original_name).suffix or ext
        elif "." in url.split("/")[-1]:
            ext = Path(url.split("/")[-1]).suffix or ext

        # 如果没有扩展名，先下载头信息或直接下载后检测?
        # 简单起见，先用 uuid 生成文件名，扩展名尽量保留
        token = uuid.uuid4().hex[:12]
        safe_name = "resource"
        if original_name:
            safe_name = Path(original_name).stem

        # 暂时无法确定准确 MIME，先下载
        # 注意：build_filename 需要 mime，这里我们可能需要先下载再重命名，或者直接用通用扩展名
        # 为了简化，我们先生成一个临时文件名
        temp_filename = f"{safe_name}_{token}{ext}"

        # 构建保存路径
        save_dir = self.root / session_id / kind / category
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / temp_filename

        # 2. 下载文件
        download_file(url, file_path, timeout=timeout)

        # 3. 检测真实 MIME 类型并重命名 (可选，但推荐)
        mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        real_ext = mime_to_extension(mime)
        if real_ext != ext and real_ext != ".bin":
            new_filename = f"{safe_name}_{token}{real_ext}"
            new_path = save_dir / new_filename
            file_path.rename(new_path)
            file_path = new_path
            temp_filename = new_filename

        # 4. 创建元数据对象
        # 判断是视频、音频还是图片
        is_video = mime.startswith("video/")
        is_audio = mime.startswith("audio/")

        if is_video:
            stored = StoredVideo(
                session_id=session_id,
                name=temp_filename,
                mime_type=mime,
                path=file_path,
                created_at=time.time(),
                kind=kind,
                source_image_url=url,  # 记录来源
            )
        elif is_audio:
            stored = StoredAudio(
                session_id=session_id,
                name=temp_filename,
                mime_type=mime,
                path=file_path,
                created_at=time.time(),
                kind=kind,
            )
        else:
            stored = StoredImage(
                session_id=session_id,
                category=category,
                name=temp_filename,
                mime_type=mime,
                path=file_path,
                created_at=time.time(),
                kind=kind,
            )

        logger.info(f"资源已保存: {url} -> {file_path} ({mime})")
        return stored.local_url

    def resolve_url(
        self, url: str
    ) -> Union[StoredImage, StoredVideo, StoredAudio, None]:
        """解析 autosave:// URL 并返回对应的媒体元数据"""
        return resolve_autosave_url(self.root, url)

    def path_to_url(self, path_str: Optional[str]) -> Optional[str]:
        """将文件路径转换为 autosave:// URL"""
        return convert_path_to_autosave_url(self.root, path_str)
