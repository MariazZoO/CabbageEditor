"""
火山引擎语音合成服务接入类
支持 HTTP 非流式调用方式
"""

import json
import base64
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict
import requests


@dataclass
class AppConfig:
    """应用配置"""

    appid: str
    token: str
    cluster: str = "volcano_tts"


@dataclass
class UserConfig:
    """用户配置"""

    uid: str = "default_user"


@dataclass
class AudioConfig:
    """音频配置"""

    voice_type: str  # 音色类型
    encoding: str = "mp3"  # 音频编码格式: wav/pcm/ogg_opus/mp3
    speed_ratio: float = 1.0  # 语速 [0.1, 2]
    rate: int = 24000  # 采样率: 8000/16000/24000
    bitrate: int = 160  # 比特率 kb/s
    emotion: Optional[str] = None  # 音色情感
    enable_emotion: bool = False  # 是否启用情感
    emotion_scale: Optional[float] = None  # 情绪值 [1, 5]
    loudness_ratio: float = 1.0  # 音量调节 [0.5, 2]
    explicit_language: Optional[str] = None  # 明确语种
    context_language: Optional[str] = None  # 参考语种


@dataclass
class RequestConfig:
    """请求配置"""

    reqid: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""  # 合成文本
    text_type: str = "plain"  # 文本类型: plain/ssml
    operation: str = "query"  # 操作类型: query(非流式)/submit(流式)
    model: Optional[str] = None  # 模型版本
    silence_duration: Optional[float] = None  # 句尾静音时长
    with_timestamp: Optional[int] = None  # 是否返回时间戳
    extra_param: Optional[Dict[str, Any]] = None  # 额外参数


class TTSClient:
    """语音合成服务客户端"""

    # API 端点
    HTTP_API_V1 = "https://openspeech.bytedance.com/api/v1/tts"

    def __init__(self, app_config: AppConfig):
        """
        初始化 TTS 客户端

        Args:
            app_config: 应用配置
        """
        self.app_config = app_config
        self.session = requests.Session()

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头"""
        return {
            "Authorization": f"Bearer;{self.app_config.token}",
            "Content-Type": "application/json",
        }

    def _build_request_body(
        self,
        audio_config: AudioConfig,
        request_config: RequestConfig,
        user_config: Optional[UserConfig] = None,
    ) -> Dict[str, Any]:
        """构建请求体"""
        if user_config is None:
            user_config = UserConfig()

        # 构建基础请求体
        body = {
            "app": asdict(self.app_config),
            "user": asdict(user_config),
            "audio": {k: v for k, v in asdict(audio_config).items() if v is not None},
            "request": {},
        }

        # 构建请求配置
        request_dict = asdict(request_config)
        for key, value in request_dict.items():
            if value is not None:
                if key == "extra_param" and isinstance(value, dict):
                    body["request"][key] = json.dumps(value)
                else:
                    body["request"][key] = value

        return body

    def synthesize_http(
        self,
        text: str,
        audio_config: AudioConfig,
        user_config: Optional[UserConfig] = None,
        extra_param: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        HTTP 非流式语音合成

        Args:
            text: 待合成文本
            audio_config: 音频配置
            user_config: 用户配置
            extra_param: 额外参数

        Returns:
            包含音频数据和元信息的字典
        """
        request_config = RequestConfig(
            text=text, operation="query", extra_param=extra_param
        )

        body = self._build_request_body(audio_config, request_config, user_config)
        headers = self._build_headers()

        try:
            response = self.session.post(
                self.HTTP_API_V1, headers=headers, json=body, timeout=30
            )
            response.raise_for_status()

            result = response.json()

            # 检查错误码
            if result.get("code") != 3000:
                raise Exception(f"TTS Error: {result.get('message', 'Unknown error')}")

            # 解码音频数据
            audio_data = base64.b64decode(result.get("data", ""))

            return {
                "reqid": result.get("reqid"),
                "audio": audio_data,
                "duration": result.get("addition", {}).get("duration"),
                "code": result.get("code"),
                "message": result.get("message"),
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP request failed: {str(e)}")

    def save_audio(self, audio_data: bytes, output_path: str):
        """
        保存音频文件

        Args:
            audio_data: 音频二进制数据
            output_path: 输出文件路径
        """
        with open(output_path, "wb") as f:
            f.write(audio_data)


def create_tts_client(appid: str, access_token: str) -> TTSClient:
    """
    创建 TTS 客户端的便捷函数

    Args:
        appid: 应用 ID
        access_token: 访问令牌

    Returns:
        TTSClient 实例
    """
    app_config = AppConfig(appid=appid, token=access_token)
    return TTSClient(app_config)
