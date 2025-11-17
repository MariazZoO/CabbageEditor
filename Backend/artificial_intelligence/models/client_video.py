"""
使用轮询组件的视频生成示例
演示如何提交异步任务并轮询结果
"""

import base64
from http import HTTPStatus
from dashscope import VideoSynthesis
import mimetypes
import dashscope
import os
from datetime import datetime
from pathlib import Path
from PIL import Image
from task_poller import TaskPoller

# 配置API
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
api_key = "sk-33989625f0ca49f896e6e12a8ac780cf"


def encode_file(file_path):
    """Base64编码图片文件"""
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError("不支持或无法识别的图像格式")
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded_string}"


def resize_image_with_constraints(
    image_path: str,
    target_width: int = None,
    target_height: int = None,
    max_size: int = 2000,
    min_size: int = 360,
):
    """
    调整图片分辨率，确保宽高在指定范围内

    参数:
    - image_path: 图片路径
    - target_width: 目标宽度（可选）
    - target_height: 目标高度（可选）
    - max_size: 最大尺寸，默认2000
    - min_size: 最小尺寸，默认360

    返回:
    - 调整后的图片路径
    """
    # 打开图片
    img = Image.open(image_path)
    original_width, original_height = img.size

    print(f"原始尺寸: {original_width}x{original_height}")

    # 如果指定了目标宽高，验证范围
    if target_width is not None:
        if target_width < min_size or target_width > max_size:
            raise ValueError(
                f"目标宽度必须在 [{min_size}, {max_size}] 范围内，当前值: {target_width}"
            )

    if target_height is not None:
        if target_height < min_size or target_height > max_size:
            raise ValueError(
                f"目标高度必须在 [{min_size}, {max_size}] 范围内，当前值: {target_height}"
            )

    # 计算新尺寸
    if target_width and target_height:
        # 指定了宽和高
        new_width = target_width
        new_height = target_height
    elif target_width:
        # 只指定了宽度，按比例计算高度
        ratio = target_width / original_width
        new_width = target_width
        new_height = int(original_height * ratio)
    elif target_height:
        # 只指定了高度，按比例计算宽度
        ratio = target_height / original_height
        new_width = int(original_width * ratio)
        new_height = target_height
    else:
        # 未指定，自动调整以满足范围要求
        new_width = original_width
        new_height = original_height

        # 如果超过最大值，等比例缩小
        if new_width > max_size or new_height > max_size:
            ratio = min(max_size / new_width, max_size / new_height)
            new_width = int(new_width * ratio)
            new_height = int(new_height * ratio)

        # 如果小于最小值，等比例放大
        if new_width < min_size or new_height < min_size:
            ratio = max(min_size / new_width, min_size / new_height)
            new_width = int(new_width * ratio)
            new_height = int(new_height * ratio)

    # 再次确保在范围内
    new_width = max(min_size, min(max_size, new_width))
    new_height = max(min_size, min(max_size, new_height))

    print(f"调整后尺寸: {new_width}x{new_height}")

    # 调整图片大小
    if (new_width, new_height) != (original_width, original_height):
        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 保存调整后的图片
        output_path = Path(image_path).parent / f"resized_{Path(image_path).name}"
        resized_img.save(output_path, quality=95)

        print(f"✓ 图片已调整并保存到: {output_path}")
        return str(output_path)
    else:
        print("✓ 图片尺寸已符合要求，无需调整")
        return image_path


def upload_local_image(
    image_path: str,
    resize: bool = True,
    target_width: int = None,
    target_height: int = None,
):
    """
    上传本地图片并转换为可用格式

    参数:
    - image_path: 本地图片路径
    - resize: 是否调整分辨率，默认True
    - target_width: 目标宽度（可选）
    - target_height: 目标高度（可选）

    返回:
    - 图片URL（file:// 或 base64格式）
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"图片文件不存在: {image_path}")

    print(f"\n📷 处理本地图片: {image_path}")

    # 调整分辨率
    if resize:
        processed_path = resize_image_with_constraints(
            image_path, target_width=target_width, target_height=target_height
        )
    else:
        # 不调整，但仍需验证尺寸
        img = Image.open(image_path)
        width, height = img.size
        if width < 360 or width > 2000 or height < 360 or height > 2000:
            raise ValueError(
                f"图片尺寸 {width}x{height} 不符合要求，宽高必须在 [360, 2000] 范围内"
            )
        processed_path = image_path
        print(f"原始尺寸: {width}x{height}")

    # 返回 file:// URL（推荐方式）
    # 或者使用 Base64 编码
    # return encode_file(processed_path)

    # 使用绝对路径
    absolute_path = os.path.abspath(processed_path)
    file_url = f"file://{absolute_path}"
    print(f"✓ 图片准备完成: {file_url}\n")

    return file_url


def submit_video_task(
    prompt: str = None,
    img_url: str = None,
    local_image_path: str = None,
    target_width: int = None,
    target_height: int = None,
):
    """
    提交视频生成任务（异步方式）

    参数:
    - prompt: 文本提示词
    - img_url: 在线图片URL
    - local_image_path: 本地图片路径（与img_url二选一）
    - target_width: 目标宽度（仅在使用本地图片时有效）
    - target_height: 目标高度（仅在使用本地图片时有效）

    返回:
    - task_id: 任务ID，用于后续轮询
    """
    # 处理图片输入
    if local_image_path:
        print(f"使用本地图片: {local_image_path}")
        img_url = upload_local_image(
            local_image_path,
            resize=True,
            target_width=target_width,
            target_height=target_height,
        )
    elif not img_url:
        # 使用默认图片
        img_url = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250925/wpimhv/rap.png"

    # 使用默认提示词或自定义提示词
    if not prompt:
        prompt = (
            "一幅都市奇幻艺术的场景。一个充满动感的涂鸦艺术角色。一个由喷漆所画成的少年，正从一面混凝土墙上活过来。"
            "他一边用极快的语速演唱一首英文rap，一边摆着一个经典的、充满活力的说唱歌手姿势。场景设定在夜晚一个充满都市感的铁路桥下。"
            "灯光来自一盏孤零零的街灯，营造出电影般的氛围，充满高能量和惊人的细节。视频的音频部分完全由少年的rap构成，没有其他对话或杂音。"
        )

    print("正在提交视频生成任务...")
    print(f"图片来源: {img_url[:80]}...")

    # 使用异步调用 (async_call)
    rsp = VideoSynthesis.async_call(
        api_key=api_key,
        model="wan2.2-i2v-flash",
        prompt=prompt,
        img_url=img_url,
        resolution="720P",
        prompt_extend=True,
        watermark=False,
        negative_prompt="",
        seed=12345,
    )

    if rsp.status_code == HTTPStatus.OK:
        task_id = rsp.output.task_id
        task_status = rsp.output.task_status
        print("✓ 任务已提交")
        print(f"  任务ID: {task_id}")
        print(f"  初始状态: {task_status}")
        return task_id
    else:
        raise Exception(
            f"任务提交失败: status_code={rsp.status_code}, "
            f"code={rsp.code}, message={rsp.message}"
        )


def poll_video_task(task_id: str):
    """
    轮询视频生成任务状态

    参数:
    - task_id: 任务ID

    返回:
    - 包含视频URL的完整响应数据
    """
    poller = TaskPoller(api_key=api_key, interval=5.0, timeout=600)
    return poller.poll(task_id)


def main():
    """主函数：提交任务并轮询结果"""

    # ========== 配置区域 ==========
    # 在这里配置你的图片和提示词

    # 方式1: 使用在线图片URL
    USE_ONLINE_IMAGE = False
    ONLINE_IMAGE_URL = "https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20250925/wpimhv/rap.png"

    # 方式2: 使用本地图片（推荐）
    USE_LOCAL_IMAGE = True
    LOCAL_IMAGE_PATH = "img_cache/7be4ecf5a1e14473827038e5f6507472.png"  # 修改为你的图片路径
    TARGET_WIDTH = 1280  # 可选：指定目标宽度（360-2000）
    TARGET_HEIGHT = None  # 可选：指定目标高度（360-2000），留空则按比例自动计算

    # 自定义提示词（可选）
    CUSTOM_PROMPT = "masterpiece, best quality, 1girl, anime style, long brown hair blowing in the wind, \
    grey hoodie, blue skirt, standing on a high cliff, looking back, overlooking the vast ocean at sunset, \
    beautiful sky with dramatic clouds, sun rays, cinematic lighting, wide angle, breathtaking view, \
    reflection on water, distant mountains, peaceful"  # 留空则使用默认提示词
    # CUSTOM_PROMPT = "你的自定义提示词..."

    # ========== 配置区域结束 ==========

    try:
        # 步骤1: 提交异步任务
        if USE_LOCAL_IMAGE:
            task_id = submit_video_task(
                prompt=CUSTOM_PROMPT,
                local_image_path=LOCAL_IMAGE_PATH,
                target_width=TARGET_WIDTH,
                target_height=TARGET_HEIGHT,
            )
        elif USE_ONLINE_IMAGE:
            task_id = submit_video_task(prompt=CUSTOM_PROMPT, img_url=ONLINE_IMAGE_URL)
        else:
            # 使用默认图片
            task_id = submit_video_task(prompt=CUSTOM_PROMPT)

        print("\n" + "-" * 50)

        # 步骤2: 轮询任务状态
        result = poll_video_task(task_id)

        # 步骤3: 获取视频URL并下载
        video_url = result.get("output", {}).get("video_url")
        if video_url:
            print("\n🎬 视频生成成功！")
            print(f"📥 下载链接: {video_url}")

            # 自动下载视频到本地
            download_video(video_url)

    except TimeoutError as e:
        print(f"\n❌ 超时: {e}")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


def download_video(video_url: str, output_path: str = None):
    """
    下载视频文件并显示进度

    参数:
    - video_url: 视频URL
    - output_path: 保存路径（可选，默认使用时间戳命名）

    返回:
    - 保存的文件路径
    """
    import requests

    # 如果未指定输出路径，使用时间戳生成文件名
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"video_{timestamp}.mp4"

    # 确保输出目录存在
    output_dir = Path(output_path).parent
    if output_dir != Path("."):
        output_dir.mkdir(parents=True, exist_ok=True)

    print("\n📦 正在下载视频...")
    print(f"   保存路径: {output_path}")

    try:
        # 发送请求，启用流式下载
        response = requests.get(video_url, stream=True, timeout=30)
        response.raise_for_status()

        # 获取文件总大小
        total_size = int(response.headers.get("content-length", 0))
        block_size = 8192  # 8KB
        downloaded_size = 0

        # 开始下载
        with open(output_path, "wb") as f:
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
                            f"\r   进度: {progress:.1f}% ({downloaded_mb:.2f}MB / {total_mb:.2f}MB)",
                            end="",
                        )

        print()  # 换行
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print("✓ 视频下载完成！")
        print(f"   文件大小: {file_size_mb:.2f} MB")
        print(f"   保存位置: {os.path.abspath(output_path)}")

        return output_path

    except Exception as e:
        print(f"\n✗ 下载失败: {e}")
        # 如果下载失败，删除不完整的文件
        if os.path.exists(output_path):
            os.remove(output_path)
        raise


if __name__ == "__main__":
    main()
