"""
语音合成工具 - 使用火山引擎TTS进行HTTP非流式语音合成
"""

from __future__ import annotations

import json
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from Backend.artificial_intelligence.config.ai_config import AIConfig
from Backend.artificial_intelligence.models.tts_client import (
    create_tts_client,
    AudioConfig,
)


class TextToSpeechInput(BaseModel):
    """文本转语音的输入参数"""

    text: str = Field(description="待合成的文本内容")
    voice_type: str = Field(
        default="zh_female_cancan_mars_bigtts",
        description="音色类型，例如：zh_female_cancan_mars_bigtts（女声）、zh_male_M392_conversation_wvae_bigtts（男声）",
    )
    speed_ratio: float = Field(
        default=1.0,
        description="语速比例，范围 [0.1, 2.0]，1.0 为正常速度",
    )
    loudness_ratio: float = Field(
        default=1.0,
        description="音量比例，范围 [0.5, 2.0]，1.0 为正常音量",
    )
    encoding: str = Field(
        default="mp3", description="音频格式，可选：mp3、wav、ogg_opus、pcm"
    )
    rate: int = Field(default=24000, description="采样率，可选：8000、16000、24000")
    max_wait_seconds: int = Field(
        default=60, description="最大等待时间（秒）"
    )
    poll_interval: float = Field(
        default=2.0, description="轮询间隔（秒）"
    )


def load_tts_tools(config: AIConfig):
    """
    加载语音合成工具

    该工具使用火山引擎TTS进行语音合成，支持：
    - 多种音色选择
    - 语速和音量调节
    - 多种音频格式输出
    - 返回云端音频 URL

    Args:
        config: 应用配置

    Returns:
        StructuredTool 列表
    """

    # 从配置中获取TTS凭证
    tts_config = config.tts
    appid = tts_config.appid
    token = tts_config.token

    if not appid or not token:
        print(
            "[警告] 未配置火山引擎TTS凭证，语音合成工具将不可用。"
            "请在配置文件中配置 tts.appid 和 tts.token"
        )
        return []

    # 创建TTS客户端
    tts_client = create_tts_client(appid=appid, access_token=token)

    def _text_to_speech(
        text: str,
        voice_type: str = "zh_female_cancan_mars_bigtts",
        speed_ratio: float = 1.0,
        loudness_ratio: float = 1.0,
        encoding: str = "mp3",
        rate: int = 24000,
        max_wait_seconds: int = 60,
        poll_interval: float = 2.0,
    ) -> str:
        """
        文本转语音

        Args:
            text: 待合成的文本
            voice_type: 音色类型
            speed_ratio: 语速比例
            loudness_ratio: 音量比例
            encoding: 音频格式
            rate: 采样率
            max_wait_seconds: 最大等待时间
            poll_interval: 轮询间隔

        Returns:
            JSON 格式的合成结果
        """
        try:
            # 验证输入
            if not text or not text.strip():
                return json.dumps(
                    {"type": "tts", "status": "error", "error": "文本内容不能为空"},
                    ensure_ascii=False,
                )

            if len(text) > 1000:
                return json.dumps(
                    {
                        "type": "tts",
                        "status": "error",
                        "error": "文本长度超过1000字符，请分段合成",
                    },
                    ensure_ascii=False,
                )

            if not (0.1 <= speed_ratio <= 2.0):
                return json.dumps(
                    {
                        "type": "tts",
                        "status": "error",
                        "error": "语速比例应在 0.1 到 2.0 之间",
                    },
                    ensure_ascii=False,
                )

            if not (0.5 <= loudness_ratio <= 2.0):
                return json.dumps(
                    {
                        "type": "tts",
                        "status": "error",
                        "error": "音量比例应在 0.5 到 2.0 之间",
                    },
                    ensure_ascii=False,
                )

            # 配置音频参数
            audio_config = AudioConfig(
                voice_type=voice_type,
                encoding=encoding,
                speed_ratio=speed_ratio,
                rate=rate,
                loudness_ratio=loudness_ratio,
            )

            # 异步模式：提交任务并轮询
            result = tts_client.synthesize_async(
                text=text,
                audio_config=audio_config,
                max_wait_seconds=max_wait_seconds,
                poll_interval=poll_interval,
            )

            return json.dumps(
                {
                    "type": "tts",
                    "status": "success",
                    "task_id": result.get("task_id"),
                    "audio_url": result.get("audio_url"),
                    "duration": result.get("duration"),
                    "req_text_length": result.get("req_text_length"),
                    "url_expire_time": result.get("url_expire_time"),
                    "encoding": encoding,
                    "voice_type": voice_type,
                    "speed_ratio": speed_ratio,
                    "loudness_ratio": loudness_ratio,
                },
                ensure_ascii=False,
            )

        except Exception as e:
            return json.dumps(
                {"type": "tts", "status": "error", "error": str(e)},
                ensure_ascii=False,
            )

    # 创建结构化工具
    tool = StructuredTool.from_function(
        func=_text_to_speech,
        name="text_to_speech",
        description="使用火山引擎TTS将文本转换为语音。异步提交任务并返回音频URL，支持多种音色、语速、音量和格式调整。",
        args_schema=TextToSpeechInput,
    )

    return [tool]


__all__ = ["load_tts_tools"]
