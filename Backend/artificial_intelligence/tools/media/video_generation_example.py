"""
视频生成使用示例
展示如何使用重构后的视频生成模块
"""

import sys
import base64
from pathlib import Path

# 添加项目根目录到 Python 路径（必须在导入 Backend 之前）
_project_root = Path(__file__).parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from Backend.artificial_intelligence.service import handle_video_generation
from Backend.artificial_intelligence.config.config import get_app_config
from Backend.artificial_intelligence.tools.media.video_tools import load_video_tools


def image_to_base64_uri(image_path: str | Path) -> str:
    """
    从本地读取图片并转换为 base64 data URI。

    参数:
        image_path: 图片文件路径（字符串或 Path 对象）

    返回:
        base64 编码的 data URI，格式为 "data:image/xxx;base64,..."

    示例:
        >>> uri = image_to_base64_uri("/path/to/image.png")
        >>> print(uri[:50])  # 显示前50个字符
        data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...
    """
    import mimetypes

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    if not path.is_file():
        raise ValueError(f"路径不是文件: {image_path}")

    # 读取图片文件并转换为 base64
    image_data = path.read_bytes()
    b64_data = base64.b64encode(image_data).decode("utf-8")

    # 获取 MIME 类型
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type or not mime_type.startswith("image/"):
        # 根据文件扩展名猜测
        ext = path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")

    # 构建 data URI
    return f"data:{mime_type};base64,{b64_data}"


def example_generate_video():
    """
    示例：使用 handle_video_generation 服务接口生成视频
    """
    # 示例请求数据
    request = {
        "prompt": (
            "masterpiece, best quality, 1girl, anime style, "
            "long brown hair blowing in the wind, grey hoodie, blue skirt, "
            "standing on a high cliff, looking back, "
            "overlooking the vast ocean at sunset, "
            "beautiful sky with dramatic clouds, sun rays, "
            "cinematic lighting, wide angle, breathtaking view, "
            "reflection on water, distant mountains, peaceful"
        ),
        "image_url": "img_cache/7be4ecf5a1e14473827038e5f6507472.png",  # 本地图片路径
        "session_id": "test_session",
        "resolution": "720P",  # 可选：480P、720P、1080P
        "prompt_extend": True,  # 可选：是否扩展提示词
        "download_video": True,  # 可选：是否下载视频到本地
    }

    # 调用服务接口
    print("=" * 60)
    print("视频生成示例")
    print("=" * 60)

    result_json = handle_video_generation(request)

    # 解析结果
    import json

    result = json.loads(result_json)

    print("\n生成结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("status") == "success":
        print("\n✓ 视频生成成功！")
        print(f"远程视频 URL: {result.get('video_url')}")

        if "local_video" in result:
            local = result["local_video"]
            print("\n本地视频信息:")
            print(f"  文件名: {local['name']}")
            print(f"  保存路径: {local['path']}")
            print(f"  autosave URL: {local['url']}")
            print(f"  文件大小: {local['file_size_mb']:.2f} MB")
    else:
        print(f"\n✗ 视频生成失败: {result.get('content')}")


def example_using_tool():
    """
    示例：通过 LangChain Tool 接口使用视频生成
    """
    config = get_app_config()

    # 加载视频生成工具
    tools = load_video_tools(config)
    if not tools:
        print("视频生成工具未启用或配置不正确")
        print("请检查配置文件中的 [media.video] 部分")
        return

    video_tool = tools[0]

    # 调用工具
    try:
        result = video_tool.invoke(
            {
                "prompt": "一只猫趴在毛毯上打瞌睡",
                "image_url": image_to_base64_uri(
                    "autosave/test_session/generated/generated/generated-d272858ae4bb41f69bc0c7b9d019793c_746e4038.png"
                ),
                "resolution": "720P",
                "prompt_extend": True,
            }
        )

        print("视频生成结果：")
        print(result)
    except Exception as e:
        print(f"调用失败：{e}")


if __name__ == "__main__":
    # 运行基本示例
    example_generate_video()

    # 取消注释以运行工具接口示例：
    # example_using_tool()
