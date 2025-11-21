import unittest
import json
from unittest.mock import MagicMock, patch
import sys
import os

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from Backend.artificial_intelligence.service.text import handle_text_generation
from Backend.artificial_intelligence.service.image import handle_image_generation
from Backend.artificial_intelligence.service.video import handle_video_generation
from Backend.artificial_intelligence.service.speech import handle_speech_generation
from Backend.artificial_intelligence.service.music import handle_music_generation
from Backend.artificial_intelligence.service.integrated import (
    handle_integrated_entrance,
)


class TestServiceErrorHandling(unittest.TestCase):
    """测试各服务的错误处理机制，确保错误响应也是完整的三层结构"""

    def validate_error_structure(self, response_str, expected_interface_type):
        """验证错误响应的三层结构"""
        try:
            data = json.loads(response_str)
        except json.JSONDecodeError:
            self.fail("Error response is not valid JSON")

        # 第一层：顶层结构
        self.assertIn("session_id", data)
        self.assertIn("error_code", data)
        self.assertIn("status_info", data)
        self.assertIn("llm_content", data)
        self.assertIn("metadata", data)

        # 错误响应应该有 error_code > 0
        self.assertGreater(data["error_code"], 0, "error_code should be > 0 for errors")
        self.assertTrue(data["status_info"], "status_info should contain error message")

        # 第二层：llm_content 应该包含错误信息（不应该为空）
        self.assertIsInstance(data["llm_content"], list)
        self.assertGreater(
            len(data["llm_content"]), 0, "llm_content should not be empty for errors"
        )

        content = data["llm_content"][0]
        self.assertIn("role", content)
        self.assertIn("interface_type", content)
        self.assertIn("sent_time_stamp", content)
        self.assertIn("part", content)

        self.assertEqual(content["interface_type"], expected_interface_type)
        self.assertIsInstance(content["part"], list)

        # 第三层：part 应该包含错误详情
        self.assertGreater(len(content["part"]), 0, "part should contain error details")
        error_part = content["part"][0]
        self.assertEqual(error_part["content_type"], "text")
        self.assertIn("content_text", error_part)
        self.assertTrue(
            error_part["content_text"], "content_text should contain error message"
        )

        # 验证 parameter 包含错误标识
        if "parameter" in error_part:
            self.assertIn("error", error_part["parameter"])
            self.assertTrue(error_part["parameter"]["error"])
            self.assertIn("exception_type", error_part["parameter"])

        print(
            f"\n[{expected_interface_type}] Error Structure Valid: {data['status_info']}"
        )

    @patch("Backend.artificial_intelligence.tools.text.load_text_tools")
    @patch("Backend.artificial_intelligence.service.text.get_ai_config")
    def test_text_generation_missing_content(self, mock_get_config, mock_load_tools):
        """测试文本生成缺少内容时的错误处理"""
        mock_tool = MagicMock()
        mock_tool.name = "generate_product_text"
        mock_load_tools.return_value = [mock_tool]

        # 空的 llm_content
        payload = {
            "session_id": "test_error",
            "llm_content": [],
            "metadata": {"test": "error_case"},
        }

        response = handle_text_generation(payload)
        self.validate_error_structure(response, "text")

    @patch("Backend.artificial_intelligence.tools.media.image_tools.load_image_tools")
    @patch("Backend.artificial_intelligence.service.image.get_ai_config")
    def test_image_generation_tool_error(self, mock_get_config, mock_load_tools):
        """测试图像生成工具返回错误的处理"""
        mock_tool = MagicMock()
        # 模拟工具返回包含 error 的 Envelope
        mock_tool.func.return_value = json.dumps({
            "session_id": "test_sid",
            "error_code": 1,
            "status_info": "API配额已用尽",
            "llm_content": [],
            "metadata": {}
        })
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_error",
            "llm_content": [
                {
                    "role": "user",
                    "part": [{"content_type": "text", "content_text": "Draw something"}],
                }
            ],
            "metadata": {},
        }

        response = handle_image_generation(payload)
        self.validate_error_structure(response, "image")

        data = json.loads(response)
        self.assertIn("API配额已用尽", data["status_info"])

    @patch("Backend.artificial_intelligence.tools.media.video_tools.load_video_tools")
    @patch("Backend.artificial_intelligence.service.video.get_ai_config")
    def test_video_generation_missing_params(self, mock_get_config, mock_load_tools):
        """测试视频生成缺少必需参数的错误处理"""
        mock_load_tools.return_value = [MagicMock()]

        # 缺少 image_url
        payload = {
            "session_id": "test_error",
            "llm_content": [
                {
                    "role": "user",
                    "part": [{"content_type": "text", "content_text": "Animate this"}],
                }
            ],
            "metadata": {},
        }

        response = handle_video_generation(payload)
        self.validate_error_structure(response, "video")

        data = json.loads(response)
        # Service raises "缺少 prompt 或 image_url"
        self.assertTrue(
            "image_url" in data["status_info"].lower() or "prompt" in data["status_info"].lower()
        )

    @patch("Backend.artificial_intelligence.tools.media.speech_tools.load_speech_tools")
    @patch("Backend.artificial_intelligence.service.speech.get_ai_config")
    def test_speech_generation_empty_url(self, mock_get_config, mock_load_tools):
        """测试语音合成返回空URL的错误处理"""
        mock_tool = MagicMock()
        # 模拟工具返回成功 Envelope 但没有有效内容
        mock_tool.func.return_value = json.dumps({
            "session_id": "test_sid",
            "error_code": 0,
            "status_info": "success",
            "llm_content": [
                {
                    "role": "tool",
                    "interface_type": "speech",
                    "part": []  # Empty parts
                }
            ],
            "metadata": {}
        })
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_error",
            "llm_content": [
                {
                    "role": "user",
                    "part": [{"content_type": "text", "content_text": "Hello"}],
                }
            ],
            "metadata": {},
        }

        response = handle_speech_generation(payload)
        self.validate_error_structure(response, "speech")

        data = json.loads(response)
        # Service raises "语音合成未返回有效的音频部分"
        self.assertIn("有效", data["status_info"])

    @patch("Backend.artificial_intelligence.tools.media.music_tools.load_music_tools")
    @patch("Backend.artificial_intelligence.service.music.get_ai_config")
    def test_music_generation_empty_audio_list(self, mock_get_config, mock_load_tools):
        """测试音乐生成返回空列表的错误处理"""
        mock_tool = MagicMock()
        # 模拟工具返回成功 Envelope 但没有有效内容
        mock_tool.func.return_value = json.dumps({
            "session_id": "test_sid",
            "error_code": 0,
            "status_info": "success",
            "llm_content": [
                {
                    "role": "tool",
                    "interface_type": "music",
                    "part": []  # Empty parts
                }
            ],
            "metadata": {}
        })
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_error",
            "llm_content": [
                {
                    "role": "user",
                    "part": [{"content_type": "text", "content_text": "Jazz music"}],
                }
            ],
            "metadata": {},
        }

        response = handle_music_generation(payload)
        self.validate_error_structure(response, "music")

        data = json.loads(response)
        # Service raises "音乐生成未返回有效的音频部分"
        self.assertIn("有效", data["status_info"])

    @patch("Backend.artificial_intelligence.service.integrated.process_chat_request")
    def test_integrated_exception_handling(self, mock_process):
        """测试综合接口异常处理"""
        # 模拟 process_chat_request 抛出异常
        mock_process.side_effect = RuntimeError("对话处理失败")

        payload = {
            "session_id": "test_error",
            "llm_content": [
                {
                    "role": "user",
                    "part": [{"content_type": "text", "content_text": "Hi"}],
                }
            ],
            "metadata": {"test": "exception"},
        }

        response = handle_integrated_entrance(payload)
        self.validate_error_structure(response, "integrated")

        data = json.loads(response)
        self.assertIn("对话处理失败", data["status_info"])
        self.assertEqual(data["metadata"]["test"], "exception")

    def test_invalid_payload(self):
        """测试各服务对无效 payload 的处理"""
        services = [
            (handle_text_generation, "text"),
            (handle_image_generation, "image"),
            (handle_video_generation, "video"),
            (handle_speech_generation, "speech"),
            (handle_music_generation, "music"),
            (handle_integrated_entrance, "integrated"),
        ]

        for handler, interface_type in services:
            with self.subTest(interface_type=interface_type):
                # 传入非字典的 payload
                response = handler(None)
                data = json.loads(response)
                self.assertGreater(data["error_code"], 0)
                self.assertIsInstance(data["llm_content"], list)


if __name__ == "__main__":
    unittest.main()
