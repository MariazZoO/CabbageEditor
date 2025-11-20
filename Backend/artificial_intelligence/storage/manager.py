"""
媒体存储管理器
"""
from __future__ import annotations

import logging
import mimetypes
import time
import uuid
from pathlib import Path
from threading import RLock
from typing import Any, List, Optional, Tuple, Union

from .models import StoredImage, StoredVideo
from .utils import (
    AUTOSAVE_URL_SCHEME,
    category_label,
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
    - 媒体文件的查询和管理
    - autosave:// URL 的构建和解析
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

    # ========================================================================
    # 核心资源保存方法 (URL优先)
    # ========================================================================

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
        # 判断是视频还是图片
        is_video = mime.startswith("video/")

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
            with self._lock:
                self._videos.setdefault(session_id, []).append(stored)
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
            with self._lock:
                if kind == "uploads":
                    self._uploads.setdefault(session_id, {})[category] = stored
                else:
                    self._generated_images.setdefault(session_id, []).append(stored)

        logger.info(f"资源已保存: {url} -> {file_path} ({mime})")
        return stored.local_url

    # ========================================================================
    # 查询与获取
    # ========================================================================

    def get_latest_upload(
        self, session_id: str, category: str
    ) -> Optional[StoredImage]:
        """获取最新上传的图片"""
        with self._lock:
            return self._uploads.get(session_id, {}).get(category)

    def get_latest_pair(
        self, session_id: str
    ) -> Tuple[Optional[StoredImage], Optional[StoredImage]]:
        """获取最新的产品图和场景图"""
        with self._lock:
            uploads = self._uploads.get(session_id, {})
            return uploads.get("product"), uploads.get("scene")

    def list_generated_images(self, session_id: str) -> List[StoredImage]:
        """列出会话中生成的所有图片"""
        with self._lock:
            return list(self._generated_images.get(session_id, []))

    def list_videos(self, session_id: str) -> List[StoredVideo]:
        """列出会话中的所有视频"""
        with self._lock:
            return list(self._videos.get(session_id, []))

    def register_reference(
        self, session_id: str, category: str, stored: StoredImage
    ) -> None:
        """注册引用图片"""
        with self._lock:
            self._uploads.setdefault(session_id, {})[category] = stored

    # ========================================================================
    # URL 解析与构建
    # ========================================================================

    def resolve_url(self, url: str) -> Union[StoredImage, StoredVideo, None]:
        """解析 autosave:// URL 并返回对应的媒体元数据"""
        return resolve_autosave_url(self.root, url)

    def path_to_url(self, path_str: Optional[str]) -> Optional[str]:
        """将文件路径转换为 autosave:// URL"""
        return convert_path_to_autosave_url(self.root, path_str)

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def clone_image_to_session(
        self, stored: Optional[StoredImage], session_id: str, category: str
    ) -> StoredImage:
        """克隆图片到新会话"""
        if stored is None:
            raise ValueError("无法克隆不存在的图片")

        # 直接文件复制
        try:
            original_path = stored.path
            if not original_path.exists():
                raise FileNotFoundError(f"源文件不存在: {original_path}")

            # 构建新路径
            ext = original_path.suffix
            token = uuid.uuid4().hex[:8]
            new_filename = f"{stored.name.split('.')[0]}_{token}{ext}"  # 简单重命名

            save_dir = self.root / session_id / "uploads" / category
            save_dir.mkdir(parents=True, exist_ok=True)
            new_path = save_dir / new_filename

            new_path.write_bytes(original_path.read_bytes())

            new_stored = StoredImage(
                session_id=session_id,
                category=category,
                name=new_filename,
                mime_type=stored.mime_type,
                path=new_path,
                created_at=time.time(),
                kind="uploads",
            )

            with self._lock:
                self._uploads.setdefault(session_id, {})[category] = new_stored

            return new_stored

        except Exception as e:
            logger.error(f"克隆图片失败: {e}")
            raise

    def register_uploads(self, request: Any) -> List[str]:
        """
        注册用户上传的图片到会话 (支持 URL 下载)
        """
        notes: List[str] = []

        if not hasattr(request, "images") or not hasattr(request, "session_id"):
            logger.warning("register_uploads: request 对象无效")
            return notes

        for attachment in request.images:
            stored = None
            try:
                # 优先处理 URL
                if hasattr(attachment, "url") and attachment.url:
                    # 检查是否已经是 autosave URL
                    if attachment.url.startswith(AUTOSAVE_URL_SCHEME):
                        stored = self.resolve_url(attachment.url)
                        if (
                            stored
                            and isinstance(stored, StoredImage)
                            and stored.session_id != request.session_id
                        ):
                            # 跨会话引用，克隆
                            stored = self.clone_image_to_session(
                                stored, request.session_id, attachment.category
                            )
                    else:
                        # 外部 URL，下载并保存
                        local_url = self.save_resource_from_url(
                            session_id=request.session_id,
                            url=attachment.url,
                            category=attachment.category,
                            original_name=getattr(attachment, "name", None),
                        )
                        # 解析回 StoredImage 以便注册引用
                        stored = self.resolve_url(local_url)

                if stored and isinstance(stored, StoredImage):
                    self.register_reference(
                        request.session_id, attachment.category, stored
                    )
                    notes.append(
                        f"已上传{category_label(attachment.category)}图片：{stored.local_url}"
                    )
                elif hasattr(attachment, "url") and attachment.url:
                    # Fallback
                    notes.append(
                        f"引用{category_label(attachment.category)}图片：{attachment.url}"
                    )
            except Exception as e:
                logger.error(f"处理上传附件失败: {e}")
                continue

        return notes
