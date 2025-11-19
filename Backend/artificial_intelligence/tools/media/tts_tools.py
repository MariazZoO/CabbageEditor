"""
语音合成工具 - 使用火山引擎TTS进行HTTP非流式语音合成
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from Backend.artificial_intelligence.config.config import AppConfig
from Backend.artificial_intelligence.models.tts_client import (
    create_tts_client,
    AudioConfig,
)
from Backend.artificial_intelligence.tools.session import get_current_session


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
    rate: int = Field(
        default=24000, description="采样率，可选：8000、16000、24000"
    )
    output_path: Optional[str] = Field(
        default=None,
        description="输出文件路径，如果提供则会保存音频文件。默认保存到 autosave/<session_id>/generated/audio/ 目录",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="会话ID。若不提供则自动采用当前活动会话。",
    )


def load_tts_tools(config: AppConfig):
    """
    加载语音合成工具

    该工具使用火山引擎TTS进行HTTP非流式语音合成，支持：
    - 多种音色选择
    - 语速和音量调节
    - 多种音频格式输出
    - 自动保存音频文件

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
        output_path: Optional[str] = None,
        session_id: Optional[str] = None,
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
            output_path: 输出文件路径
            session_id: 会话ID

        Returns:
            包含合成结果的描述字符串
        """
        try:
            # 获取当前会话ID
            active_session = session_id or get_current_session()
            
            # 验证输入
            if not text or not text.strip():
                return "❌ 错误：文本内容不能为空"

            if len(text) > 1000:
                return "❌ 错误：文本长度超过1000字符，请分段合成"

            if not (0.1 <= speed_ratio <= 2.0):
                return "❌ 错误：语速比例应在 0.1 到 2.0 之间"

            if not (0.5 <= loudness_ratio <= 2.0):
                return "❌ 错误：音量比例应在 0.5 到 2.0 之间"

            # 配置音频参数
            audio_config = AudioConfig(
                voice_type=voice_type,
                encoding=encoding,
                speed_ratio=speed_ratio,
                rate=rate,
                loudness_ratio=loudness_ratio,
            )

            # 执行合成
            result = tts_client.synthesize_http(
                text=text, audio_config=audio_config
            )

            # 确定输出路径 - 与 music_tools 保持一致
            if output_path is None:
                # 获取项目根目录（上溯3级到达 CabbageEditor/）
                audio_dir = (
                    Path(os.path.dirname(__file__)).resolve().parents[3]
                    / "autosave"
                    / active_session
                    / "generated"
                    / "audio"
                )
                audio_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成文件名，包含请求ID和简短的文本摘要
                reqid = result.get('reqid', 'unknown')[:8]
                text_preview = "".join(c for c in text[:20] if c.isalnum() or c in (" ", "-", "_"))
                filename = f"tts_{reqid}_{text_preview}.{encoding}".replace(" ", "_")
                output_path = str(audio_dir / filename)
            else:
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

            # 保存音频文件
            tts_client.save_audio(result["audio"], output_path)

            # 获取文件大小和相关信息
            file_size = os.path.getsize(output_path)
            duration = result.get("duration", 0)
            
            # 生成 autosave URL
            output_path_obj = Path(output_path)
            autosave_url = f"autosave://{active_session}/generated/audio/{output_path_obj.name}"

            return (
                f"✅ 语音合成成功\n"
                f"📊 合成结果：\n"
                f"  • 请求ID: {result.get('reqid')}\n"
                f"  • 音频时长: {duration} ms\n"
                f"  • 文件大小: {file_size} bytes\n"
                f"  • 本地路径: {output_path}\n"
                f"  • 自动保存URL: {autosave_url}\n"
                f"  • 会话ID: {active_session}\n"
                f"  • 音色: {voice_type}\n"
                f"  • 语速: {speed_ratio}x\n"
                f"  • 音量: {loudness_ratio}x"
            )

        except Exception as e:
            return f"❌ 合成失败：{str(e)}"

    # 创建结构化工具
    tool = StructuredTool.from_function(
        func=_text_to_speech,
        name="text_to_speech",
        description="使用火山引擎TTS将文本转换为语音。支持多种音色、语速、音量和格式调整。",
        args_schema=TextToSpeechInput,
    )

    return [tool]


__all__ = ["load_tts_tools"]
