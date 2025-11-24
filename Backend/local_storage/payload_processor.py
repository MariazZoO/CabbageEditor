from typing import Any, Dict
from .utils import get_media_store


def process_input_payload(payload: Dict[str, Any]):
    """
    预处理输入 Payload：将 Base64 图片转换为本地文件路径
    """
    store = get_media_store()
    session_id = payload.get("session_id", "default")
    if "llm_content" in payload and isinstance(payload["llm_content"], list):
        for content in payload["llm_content"]:
            if "part" in content and isinstance(content["part"], list):
                for part in content["part"]:
                    if part.get("content_type") == "image":
                        url = part.get("content_url", "")
                        if url.startswith("data:image"):
                            # 直接把 Base64 保存为本地文件并返回 file:// URL，前端可直接使用
                            file_url = store.save_base64_image(session_id, url)
                            part["content_url"] = file_url

    return payload


def process_output_payload(payload: Dict[str, Any]):
    """
    后处理输出 Payload：下载云端媒体资源并替换为本地 file:// URL
    """
    store = get_media_store()
    session_id = payload.get("session_id", "default")
    if "llm_content" in payload and isinstance(payload["llm_content"], list):
        for content in payload["llm_content"]:
            if "part" in content and isinstance(content["part"], list):
                for part in content["part"]:
                    c_type = part.get("content_type")
                    url = part.get("content_url", "")
                    if c_type in ["image", "video", "audio"] and url.startswith("http"):
                        local_resource_url = store.save_resource_from_url(
                            session_id=session_id,
                            url=url,
                            resource_type=c_type,
                        )

                        part["content_url"] = local_resource_url
                        print(local_resource_url)

    return payload
