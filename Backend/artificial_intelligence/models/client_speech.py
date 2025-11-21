"""
火山引擎语音合成服务接入类
支持 HTTP 异步调用方式 (v3 API)
"""

import uuid
from typing import Optional, Dict, Any, Tuple
import requests

from Backend.artificial_intelligence.models.speech_config import (
    AppConfig,
    AudioConfig,
)
from Backend.artificial_intelligence.models.utils import TaskPoller


class TTSClient:
    """语音合成服务客户端"""

    # API 端点 - v3 异步接口
    SUBMIT_API = "https://openspeech.bytedance.com/api/v3/tts/submit"
    QUERY_API = "https://openspeech.bytedance.com/api/v3/tts/query"

    def __init__(self, app_config: AppConfig):
        """
        初始化 TTS 客户端

        Args:
            app_config: 应用配置
        """
        self.app_config = app_config
        self.session = requests.Session()

    def _build_headers(self) -> Dict[str, str]:
        """构建请求头 - v3 API格式"""
        return {
            "X-Api-App-Id": self.app_config.appid,
            "X-Api-Access-Key": self.app_config.token,
            "X-Api-Resource-Id": "volc.service_type.10029",  # 大模型语音合成
            "X-Api-Request-Id": str(uuid.uuid4()),  # 客户端请求ID
            "Content-Type": "application/json",
        }

    def _build_submit_body(
        self,
        text: str,
        audio_config: AudioConfig,
        unique_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建submit请求体 - v3 API格式"""

        # 将速度和音量从比例转换为范围[-50, 100]
        speech_rate = int((audio_config.speed_ratio - 1.0) * 100)
        loudness_rate = int((audio_config.loudness_ratio - 1.0) * 100)

        body = {
            "user": {"uid": self.app_config.uid},
            "req_params": {
                "text": text,
                "speaker": audio_config.voice_type,
                "audio_params": {
                    "format": audio_config.encoding,
                    "sample_rate": audio_config.rate,
                    "speech_rate": speech_rate,
                    "loudness_rate": loudness_rate,
                },
            },
        }

        # 添加可选的unique_id
        if unique_id:
            body["unique_id"] = unique_id

        # 添加情感参数
        if audio_config.emotion:
            body["req_params"]["audio_params"]["emotion"] = audio_config.emotion
            if audio_config.emotion_scale:
                body["req_params"]["audio_params"]["emotion_scale"] = audio_config.emotion_scale

        return body

    def _build_query_body(self, task_id: str) -> Dict[str, Any]:
        """构建query请求体 - v3 API格式"""
        return {"task_id": task_id}

    def async_submit(
        self,
        text: str,
        audio_config: AudioConfig,
        unique_id: Optional[str] = None,
    ) -> str:
        """
        异步提交语音合成任务 - v3 API

        Args:
            text: 待合成文本
            audio_config: 音频配置
            unique_id: 唯一标识（可选）

        Returns:
            任务ID (task_id)
        """
        body = self._build_submit_body(text, audio_config, unique_id)
        headers = self._build_headers()

        try:
            response = self.session.post(self.SUBMIT_API, headers=headers, json=body, timeout=30)
            response.raise_for_status()

            result = response.json()

            # v3 API成功码是 20000000
            if result.get("code") != 20000000:
                error_msg = result.get("message", "Unknown error")
                raise Exception(f"TTS Submit Error [{result.get('code')}]: {error_msg}")

            task_id = result.get("data", {}).get("task_id")
            if not task_id:
                raise Exception("No task_id returned from async submit")

            return task_id

        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP request failed: {str(e)}")

    def query_task(self, task_id: str) -> Dict[str, Any]:
        """
        查询异步任务状态 - v3 API

        Args:
            task_id: 任务ID

        Returns:
            任务状态信息，包括:
            - status: SUCCESS/PROCESSING/FAILED
            - task_id: 任务ID
            - audio_url: 音频URL (成功时)
            - duration: 音频时长
            - error: 错误信息 (失败时)
        """
        body = self._build_query_body(task_id)
        headers = self._build_headers()

        try:
            response = self.session.post(self.QUERY_API, headers=headers, json=body, timeout=30)
            response.raise_for_status()

            result = response.json()
            code = result.get("code")

            # v3 API成功码是 20000000
            if code == 20000000:
                data = result.get("data", {})
                task_status = data.get("task_status")

                # task_status = 1 (Running), 2 (Success), 3 (Failure)
                if task_status == 2:  # Success
                    return {
                        "status": "SUCCESS",
                        "task_id": task_id,
                        "audio_url": data.get("audio_url"),
                        "duration": data.get("synthesize_text_length"),
                        "req_text_length": data.get("req_text_length"),
                        "url_expire_time": data.get("url_expire_time"),
                        "sentences": data.get("sentences"),
                        "code": code,
                        "message": result.get("message"),
                    }
                elif task_status == 1:  # Running
                    return {
                        "status": "PROCESSING",
                        "task_id": task_id,
                        "code": code,
                        "message": result.get("message"),
                    }
                elif task_status == 3:  # Failure
                    return {
                        "status": "FAILED",
                        "task_id": task_id,
                        "error": result.get("message", "Task failed"),
                        "code": code,
                    }
                else:
                    return {
                        "status": "UNKNOWN",
                        "task_id": task_id,
                        "error": f"Unknown task_status: {task_status}",
                        "code": code,
                    }
            else:
                # 请求失败
                return {
                    "status": "FAILED",
                    "task_id": task_id,
                    "error": result.get("message", "Unknown error"),
                    "code": code,
                }

        except requests.exceptions.RequestException as e:
            return {
                "status": "FAILED",
                "task_id": task_id,
                "error": f"Query request failed: {str(e)}",
            }

    def synthesize_async(
        self,
        text: str,
        audio_config: AudioConfig,
        max_wait_seconds: int = 60,
        poll_interval: float = 2.0,
    ) -> Dict[str, Any]:
        """
        异步语音合成（提交任务并轮询直到完成）- v3 API

        Args:
            text: 待合成文本
            audio_config: 音频配置
            max_wait_seconds: 最大等待时间（秒）
            poll_interval: 轮询间隔（秒）

        Returns:
            包含音频URL和元信息的字典
        """
        # 提交任务
        task_id = self.async_submit(text, audio_config)

        # 使用通用轮询器
        poller = TaskPoller(interval=poll_interval, timeout=max_wait_seconds)

        def check_status(tid: str) -> Tuple[str, Any, Optional[str]]:
            result = self.query_task(tid)
            status = result.get("status")

            # 映射状态到 TaskPoller 期望的状态
            # TaskPoller expects: "PENDING", "RUNNING", "PROCESSING", "SUCCEEDED", "FAILED"
            # query_task returns: "SUCCESS", "PROCESSING", "FAILED", "UNKNOWN"

            if status == "SUCCESS":
                return "SUCCEEDED", result, None
            elif status == "PROCESSING":
                return "PROCESSING", None, None
            elif status == "FAILED":
                return "FAILED", None, result.get("error")
            else:
                # UNKNOWN or others
                return "FAILED", None, f"Unknown status: {status}"

        return poller.poll(task_id, check_status)

    def save_audio(self, audio_data: bytes, output_path: str):
        """
        保存音频文件

        Args:
            audio_data: 音频二进制数据
            output_path: 输出文件路径
        """
        with open(output_path, "wb") as f:
            f.write(audio_data)


def create_speech_client(appid: str, access_token: str) -> TTSClient:
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
