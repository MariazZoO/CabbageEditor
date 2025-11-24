"""
媒体存储管理器
"""

from __future__ import annotations

import base64
import binascii
import logging
import mimetypes
import uuid
import re
import urllib.parse

from pathlib import Path
from typing import Optional

from .utils import mime_to_extension
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

    def save_base64_image(self, session_id: str, data_url: str) -> str:
        """
        保存 Base64 图片到本地，返回本地 file URL
        """
        try:
            header, encoded = data_url.split(",", 1)
            mime = header.split(":")[1].split(";")[0]
            ext = mime_to_extension(mime)

            data = base64.b64decode(encoded)

            token = uuid.uuid4().hex[:12]
            filename = f"upload_{token}{ext}"

            # 保存到 uploads 目录（确保 session_id 非空）
            safe_session = session_id or "default"
            save_dir = self.root / safe_session
            save_dir.mkdir(parents=True, exist_ok=True)

            file_path = save_dir / filename
            file_path.write_bytes(data)

            # 创建元数据对象的逻辑可以在需要时恢复，这里仅保存文件并返回本地 URL

            logger.info(f"Base64 图片已保存: {file_path}")
            # 直接返回本地 file:// URL，前端可直接使用
            return file_path.absolute().as_uri()

        except (ValueError, binascii.Error, IndexError) as e:
            logger.error(f"Base64 解码失败: {e}")
            raise

    def save_resource_from_url(
        self,
        *,
        session_id: str,
        url: str,
        resource_type: str,
        original_name: Optional[str] = None,
        timeout: int = 300,
        retries: int = 2,
        backoff_factor: float = 0.5,
    ) -> str:
        """
        从 URL 下载资源并保存，返回本地 file URL

        参数:
        - session_id: 会话ID
        - url: 远程资源 URL
        - resource_type: 资源类型提示 (例如 'image', 'video', 'audio')，用于推断默认扩展名
        - original_name: 原始文件名 (可选，用于推断扩展名)
        - timeout: 下载超时

        返回:
        - 本地 `file://...` URL（前端可以直接使用）
        """
        # 1. 确定文件名和路径
        # 尝试从 URL 或 original_name 推断扩展名，默认 .bin
        ext = ".bin"
        if original_name:
            ext = Path(original_name).suffix or ext
        elif "." in url.split("/")[-1]:
            ext = Path(url.split("/")[-1]).suffix or ext

        # 如果没有扩展名，尝试根据 category 推断一个默认扩展名（优先）
        # 简单起见，先用 uuid 生成文件名，扩展名尽量保留
        if ext == ".bin":
            rt = (resource_type or "").lower()
            if "video" in rt:
                ext = ".mp4"
            elif "audio" in rt:
                ext = ".mp3"
            elif "image" in rt or "img" in rt or "pic" in rt:
                ext = ".png"
        token = uuid.uuid4().hex[:12]
        safe_name = "resource"
        if original_name:
            safe_name = Path(original_name).stem

        temp_filename = f"{safe_name}_{token}{ext}"

        # 构建保存路径（仅按 session_id 分类）
        safe_session = session_id or "default"
        save_dir = self.root / safe_session
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / temp_filename

        # 2. 下载文件并获取响应头用于判断真实类型/文件名
        success, headers = download_file(
            url, file_path, timeout=timeout, retries=retries, backoff_factor=backoff_factor
        )

        content_type = headers.get("Content-Type") or headers.get("content-type")
        content_disp = headers.get("Content-Disposition") or headers.get(
            "content-disposition"
        )

        # 先初始化 real_ext，可以通过 Content-Disposition 或 Content-Type 填充
        real_ext = None

        # 如果服务器在 Content-Disposition 中给出了文件名，则优先使用
        if content_disp:
            # 简单解析 filename* 或 filename，支持百分号编码
            def _parse_filename(cd: str) -> Optional[str]:
                m = re.search(r"filename\*=(?P<val>[^;]+)", cd, flags=re.IGNORECASE)
                if m:
                    val = m.group("val").strip().strip('"')
                    if "''" in val:
                        val = val.split("''", 1)[1]
                    try:
                        val = urllib.parse.unquote(val)
                    except Exception:
                        pass
                    return val
                m2 = re.search(r'filename\s*=\s*"(?P<val>[^"]+)"', cd, flags=re.IGNORECASE)
                if m2:
                    return m2.group("val")
                m3 = re.search(r'filename\s*=\s*(?P<val>[^;]+)', cd, flags=re.IGNORECASE)
                if m3:
                    return m3.group("val").strip().strip('"')
                return None

            server_name = _parse_filename(content_disp)
            if server_name:
                try:
                    server_name = server_name.encode("latin-1").decode("utf-8")
                except Exception:
                    pass
                server_ext = Path(server_name).suffix
                if server_ext:
                    real_ext = server_ext
                safe_name = Path(server_name).stem or safe_name

        # 如果有 Content-Type 且还没有确定扩展名，依据其推断扩展名
        if content_type and (not real_ext or real_ext == ".bin"):
            mime = content_type.split(";")[0].strip()
            real_ext = mime_to_extension(mime)

        # 如果没有从服务器得到扩展名，继续使用之前推断的 ext
        if not real_ext or real_ext == ".bin":
            real_ext = ext

        # 如果最终扩展名与临时的不同，重命名
        if real_ext != ext and real_ext != ".bin":
            new_filename = f"{safe_name}_{token}{real_ext}"
            new_path = save_dir / new_filename
            try:
                file_path.rename(new_path)
                file_path = new_path
                temp_filename = new_filename
            except Exception:
                # 如果重命名失败，保持原文件
                logger.warning("重命名文件失败，保留原名 %s", file_path)

        final_mime = content_type or mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        logger.info(f"资源已保存: {url} -> {file_path} ({final_mime})")

        return file_path.absolute().as_uri()
