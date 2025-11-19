"""
文本到背景音乐 (BGM) 生成工具

基于 Suno API 的简单封装：根据文本提示词生成可用作背景音乐的音频。

设计目标：
- 与现有 image/video/tts 工具的风格保持一致，返回 JSON 字符串
- 支持同步等待生成完成（轮询任务详情）或立即返回任务ID
- 返回音频 URL 列表，不进行本地下载（下载功能在测试代码中实现）
- 通过环境变量或配置 provider 读取 API Key

使用前准备：
1. 在 app_config.toml 中新增一个 provider（可选）：
   [[providers]]
   name = "suno"
   type = "http"
   base_url = "https://api.sunoapi.org"  # 也可省略使用默认
   api_key_env = "SUNO_API_KEY"
2. 或直接在运行环境设置环境变量： export SUNO_API_KEY=你的密钥

核心端点（参照文档示例，可能需根据实际返回结构调整）：
- POST /generate-music  发起音乐生成
- GET  /get-music-generation-details?id=TASK_ID  查询任务进度与结果

如果 API 返回结构与假设不同，可在后续迭代中调整解析逻辑。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import requests
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.config import AppConfig

_DEFAULT_BASE_URL = "https://api.sunoapi.org"


@dataclass(frozen=True)
class SunoProviderInfo:
    base_url: str
    api_key: str


class TextToBGMInput(BaseModel):
    """文本到背景音乐生成输入"""

    prompt: str = Field(..., description="音乐内容或氛围的描述性文本提示词")
    style: Optional[str] = Field(
        default=None,
        description="可选的风格标签，例如 'lofi', 'ambient', 'fantasy', 'epic orchestral' 等",
    )
    model: str = Field(
        default="V5",
        description="Suno 模型版本，例如: V5, V4_5PLUS, V4_5, V4, V3_5",
    )
    duration: int = Field(
        default=20,
        description="期望的音乐时长（秒）。不同模型可能有上限，超出会被后端裁剪或拒绝。",
    )
    wait: bool = Field(
        default=True,
        description="是否同步等待任务完成。True 将轮询任务详情并在成功后下载音频。False 立即返回任务ID。",
    )
    max_wait_seconds: int = Field(
        default=600,
        description="最大等待时间（秒），仅在 wait=True 时生效。",
    )
    poll_interval: float = Field(
        default=3.0,
        description="轮询间隔（秒），仅在 wait=True 时生效。",
    )


# ---------------------------------------------------------------------------
# Provider / Key 解析
# ---------------------------------------------------------------------------


def _resolve_suno_provider(config: AppConfig) -> Optional[SunoProviderInfo]:
    """
    解析 Suno API 配置，优先级：
    1. config.music 配置（独立配置项）
    2. 环境变量 SUNO_API_KEY
    """
    music_cfg = config.music
    api_key = music_cfg.api_key if music_cfg else None
    base_url = music_cfg.base_url if music_cfg else _DEFAULT_BASE_URL

    # 如果没有配置，尝试从环境变量读取
    if not api_key:
        api_key = os.getenv("SUNO_API_KEY")

    if not api_key:
        return None

    return SunoProviderInfo(
        base_url=(base_url or _DEFAULT_BASE_URL).rstrip("/"), api_key=api_key.strip()
    )


# ---------------------------------------------------------------------------
# 核心调用逻辑
# ---------------------------------------------------------------------------


def _post_generate_music(provider: SunoProviderInfo, payload: dict) -> dict:
    """调用Suno API生成音乐"""
    url = f"{provider.base_url}/api/v1/generate"
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    result = resp.json() if resp.content else {}

    # 检查API响应格式: {code: 200, msg: "success", data: {taskId: "xxx"}}
    if result.get("code") != 200:
        raise Exception(
            f"API返回错误: code={result.get('code')}, msg={result.get('msg')}"
        )

    return result


def _get_music_details(provider: SunoProviderInfo, task_id: str) -> dict:
    """查询音乐生成任务详情"""
    url = f"{provider.base_url}/api/v1/generate/record-info"
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    params = {"taskId": task_id}
    resp = requests.get(url, params=params, headers=headers, timeout=60)
    resp.raise_for_status()
    result = resp.json() if resp.content else {}

    # 检查API响应格式: {code: 200, msg: "success", data: {...}}
    if result.get("code") != 200:
        raise Exception(f"查询失败: code={result.get('code')}, msg={result.get('msg')}")

    return result


# ---------------------------------------------------------------------------
# 工具加载
# ---------------------------------------------------------------------------


def load_music_tools(config: AppConfig):
    provider = _resolve_suno_provider(config)
    if provider is None:
        # 未配置 API Key 时不加载工具，保持系统正常
        print(
            "[警告] 未找到 Suno API 密钥，文本到BGM工具未启用。请设置环境变量 SUNO_API_KEY 或在 app_config.toml 中配置 provider 'suno'."
        )
        return []

    def _generate_bgm(
        prompt: str,
        style: str | None = None,
        model: str = "V5",
        duration: int = 20,
        wait: bool = True,
        max_wait_seconds: int = 600,
        poll_interval: float = 3.0,
    ) -> str:
        data = TextToBGMInput(
            prompt=prompt,
            style=style,
            model=model,
            duration=duration,
            wait=wait,
            max_wait_seconds=max_wait_seconds,
            poll_interval=poll_interval,
        )

        if not data.prompt.strip():
            return json.dumps(
                {
                    "type": "bgm_generation",
                    "status": "failed",
                    "error": "提示词不能为空",
                },
                ensure_ascii=False,
            )

        # 准备请求载荷，根据Suno API文档格式
        # customMode=true时需要style和title，instrumental决定是否纯音乐
        payload = {
            "prompt": data.prompt,
            "model": data.model,
            "customMode": bool(data.style),  # 如果有style则使用自定义模式
            "instrumental": True,  # 默认生成纯音乐(无歌词)
            "callBackUrl": "https://example.com/callback",  # 回调URL（使用占位符，实际通过轮询获取结果）
        }

        # 自定义模式下需要提供style和title
        if data.style:
            payload["style"] = data.style
            payload["title"] = data.prompt[:80]  # 使用prompt的前80字符作为标题

        # 注意：duration参数在API文档中未提及，可能不被支持
        # 如果API支持，取消下面这行的注释
        # payload["duration"] = data.duration

        try:
            initial = _post_generate_music(provider, payload)
        except Exception as e:
            return json.dumps(
                {
                    "type": "bgm_generation",
                    "status": "failed",
                    "error": f"发起生成请求失败: {e}",
                },
                ensure_ascii=False,
            )

        # 从API响应中提取taskId: {code: 200, data: {taskId: "xxx"}}
        data_obj = initial.get("data", {})
        task_id = data_obj.get("taskId") or initial.get("taskId")
        result_payload = {
            "type": "bgm_generation",
            "status": "submitted" if data.wait else "pending",
            "task_id": task_id,
            "model": data.model,
            "prompt": data.prompt,
            "style": data.style,
            "request": payload,
            "raw_response": initial,
        }

        if not data.wait or not task_id:
            return json.dumps(result_payload, ensure_ascii=False)

        # 轮询任务状态
        start = time.time()
        last_details: dict = {}
        try:
            while time.time() - start < data.max_wait_seconds:
                try:
                    details = _get_music_details(provider, task_id)
                    last_details = details
                    # API返回格式: {code: 200, data: {status: "SUCCESS/PENDING/...", ...}}
                    data_obj = details.get("data", {})
                    status = data_obj.get("status") or ""
                except Exception as poll_err:
                    last_details = {"error": f"轮询失败: {poll_err}"}
                    status = "ERROR"
                # 状态枚举: PENDING, TEXT_SUCCESS, FIRST_SUCCESS, SUCCESS,
                # CREATE_TASK_FAILED, GENERATE_AUDIO_FAILED, CALLBACK_EXCEPTION, SENSITIVE_WORD_ERROR
                if status in {
                    "SUCCESS",
                    "FIRST_SUCCESS",
                    "CREATE_TASK_FAILED",
                    "GENERATE_AUDIO_FAILED",
                    "CALLBACK_EXCEPTION",
                    "SENSITIVE_WORD_ERROR",
                    "ERROR",
                }:
                    break
                time.sleep(data.poll_interval)
        except KeyboardInterrupt:
            result_payload["status"] = "interrupted"
            result_payload["details"] = last_details
            return json.dumps(result_payload, ensure_ascii=False)

        # 解析最终状态
        data_obj = (
            last_details.get("data", {}) if isinstance(last_details, dict) else {}
        )
        status = data_obj.get("status") or "UNKNOWN"
        result_payload["status"] = status
        result_payload["details"] = last_details

        # 检查是否有错误
        error_code = data_obj.get("errorCode")
        error_message = data_obj.get("errorMessage")
        if error_code or error_message:
            result_payload["error"] = (
                f"errorCode={error_code}, errorMessage={error_message}"
            )

        # 成功则返回音频URL信息
        # 状态为 SUCCESS 或 FIRST_SUCCESS 时表示生成成功
        if status in {"SUCCESS", "FIRST_SUCCESS"}:
            # 从API响应中提取音频URL: data.response.sunoData[0].audioUrl
            response_obj = data_obj.get("response", {})
            suno_data = response_obj.get("sunoData", [])

            if isinstance(suno_data, list) and len(suno_data) > 0:
                # 保存所有音频的URL信息（不下载）
                result_payload["audio_list"] = []

                for idx, audio_item in enumerate(suno_data):
                    audio_url = audio_item.get("audioUrl")
                    if not audio_url:
                        continue

                    # 保存每个音频的信息（仅URL和元数据，不下载）
                    audio_info = {
                        "index": idx + 1,
                        "id": audio_item.get("id"),
                        "title": audio_item.get("title"),
                        "duration": audio_item.get("duration"),
                        "image_url": audio_item.get("imageUrl"),
                        "model_name": audio_item.get("modelName"),
                        "tags": audio_item.get("tags"),
                        "audio_url": audio_url,
                    }
                    result_payload["audio_list"].append(audio_info)

                # 为了向后兼容，保留 audio 字段指向第一个音频
                if result_payload["audio_list"]:
                    first_audio = result_payload["audio_list"][0]
                    result_payload["audio"] = {
                        "audio_url": first_audio["audio_url"],
                        "id": first_audio["id"],
                        "title": first_audio["title"],
                        "duration": first_audio["duration"],
                    }
                    result_payload["audio_count"] = len(result_payload["audio_list"])
            else:
                result_payload["warning"] = "未在结果中找到音频数据"

        return json.dumps(result_payload, ensure_ascii=False)

    tool = StructuredTool(
        name="generate_bgm_music",
        description=(
            "根据文本提示词生成背景音乐 (BGM)。支持指定模型版本、风格标签；"
            "可选择同步等待生成完成或立即返回任务ID。"
            "返回 JSON 字符串，包含任务ID、状态、可用的音频URL列表。"
        ),
        args_schema=TextToBGMInput,
        func=_generate_bgm,
    )

    return [tool]


__all__ = ["load_music_tools"]
