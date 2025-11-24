"""
文件下载器
"""

import logging
import time
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


def download_file(
    url: str,
    destination: Path,
    timeout: int = 300,
    chunk_size: int = 8192,
    retries: int = 2,
    backoff_factor: float = 0.5,
) -> tuple[bool, dict]:
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
    attempt = 0
    last_exc = None
    while attempt <= retries:
        try:
            logger.info(f"开始下载 (attempt {attempt + 1}): {url} -> {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with requests.Session() as session:
                response = session.get(url, stream=True, timeout=timeout)
                response.raise_for_status()
                with open(destination, "wb") as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
            logger.info(f"下载完成: {destination}")
            return True, dict(response.headers)
        except Exception as e:
            last_exc = e
            logger.warning(f"下载失败 (attempt {attempt + 1}) {url}: {e}")
            # 清理残留的文件
            if destination.exists():
                try:
                    destination.unlink()
                except OSError:
                    pass
            attempt += 1
            if attempt > retries:
                logger.error(f"所有重试失败: {url}")
                raise last_exc
            # 指数退避
            sleep_seconds = backoff_factor * (2 ** (attempt - 1))
            logger.info(f"等待 {sleep_seconds} 秒后重试")
            time.sleep(sleep_seconds)
