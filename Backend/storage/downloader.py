"""
文件下载器
"""

import logging
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


def download_file(
    url: str, destination: Path, timeout: int = 300, chunk_size: int = 8192
) -> bool:
    """
    下载文件到指定路径

    参数:
    - url: 下载链接
    - destination: 目标文件路径
    - timeout: 超时时间(秒)
    - chunk_size: 块大小

    返回:
    - bool: 是否成功
    """
    try:
        logger.info(f"开始下载: {url} -> {destination}")

        # 确保父目录存在
        destination.parent.mkdir(parents=True, exist_ok=True)

        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)

        logger.info(f"下载完成: {destination}")
        return True

    except Exception as e:
        logger.error(f"下载失败 {url}: {e}")
        # 清理可能残留的文件
        if destination.exists():
            try:
                destination.unlink()
            except OSError:
                pass
        raise
