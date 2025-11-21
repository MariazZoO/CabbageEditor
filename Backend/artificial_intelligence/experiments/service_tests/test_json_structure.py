import unittest
import json
from unittest.mock import MagicMock, patch
import sys
import os
from langchain_core.messages import AIMessage

# 添加项目根目录到 sys.path，以便导入模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from Backend.artificial_intelligence.service.text import handle_text_generation
from Backend.artificial_intelligence.service.image import handle_image_generation
from Backend.artificial_intelligence.service.video import handle_video_generation
from Backend.artificial_intelligence.service.speech import handle_speech_generation
from Backend.artificial_intelligence.service.music import handle_music_generation
from Backend.artificial_intelligence.service.integrated import (
    handle_integrated_entrance,
)


class TestServiceJsonStructure(unittest.TestCase):

    def validate_structure(self, response_str, expected_interface_type):
        """验证 JSON 响应的三层结构"""
        try:
            data = json.loads(response_str)
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON")

        # Layer 1
        self.assertIn("session_id", data)
        self.assertIn("error_code", data)
        self.assertIn("status_info", data)
        self.assertIn("llm_content", data)
        self.assertIn("metadata", data)

        if data["error_code"] != 0:
            print(f"\n[{expected_interface_type}] Error Info: {data.get('status_info')}")
        self.assertEqual(data["error_code"], 0)
        self.assertIsInstance(data["llm_content"], list)
        self.assertIsInstance(data["metadata"], dict)

        if not data["llm_content"]:
            return  # 空内容也算结构正确，但通常会有内容

        # Layer 2
        content = data["llm_content"][0]
        self.assertIn("role", content)
        self.assertIn("interface_type", content)
        self.assertIn("sent_time_stamp", content)
        self.assertIn("part", content)

        self.assertEqual(content["interface_type"], expected_interface_type)
        self.assertIsInstance(content["part"], list)

        # Layer 3
        for part in content["part"]:
            self.assertIn("content_type", part)
            # parameter 是可选的，但如果存在必须是 dict
            if "parameter" in part:
                self.assertIsInstance(part["parameter"], dict)
                # 检查 parameter 中是否包含非预期的字段 (根据 llms.txt)
                # 这里只做简单检查，确保它是字典即可

    @patch("Backend.artificial_intelligence.tools.text.load_text_tools")
    @patch("Backend.artificial_intelligence.service.text.get_ai_config")
    def test_text_generation_structure(self, mock_get_config, mock_load_tools):
        # Setup Mock
        mock_tool = MagicMock()
        mock_tool.func.return_value = json.dumps(
            {
                "session_id": "test_sid",
                "error_code": 0,
                "status_info": "success",
                "llm_content": [
                    {
                        "role": "tool",
                        "interface_type": "text",
                        "sent_time_stamp": 123,
                        "part": [
                            {
                                "content_type": "text",
                                "content_text": "Generated Text Content",
                                "parameter": {"text_type": "product"},
                            }
                        ],
                    }
                ],
                "metadata": {},
            }
        )
        mock_tool.name = "generate_product_text"
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_sid",
            "llm_content": [
                {
                    "role": "user",
                    "part": [{"content_type": "text", "content_text": "Write a poem"}],
                }
            ],
            "metadata": {"extra": "value"},  # 测试 metadata 透传
        }

        response = handle_text_generation(payload)
        self.validate_structure(response, "text")

        # 验证 metadata 透传
        data = json.loads(response)
        self.assertEqual(data["metadata"].get("extra"), "value")

    @patch("Backend.artificial_intelligence.tools.media.image_tools.load_image_tools")
    @patch("Backend.artificial_intelligence.service.image.get_ai_config")
    def test_image_generation_structure(self, mock_get_config, mock_load_tools):
        mock_tool = MagicMock()
        mock_tool.func.return_value = json.dumps(
            {
                "session_id": "test_sid",
                "error_code": 0,
                "status_info": "success",
                "llm_content": [
                    {
                        "role": "tool",
                        "interface_type": "image",
                        "sent_time_stamp": 123,
                        "part": [
                            {
                                "content_type": "image",
                                "content_url": "http://example.com/img.png",
                                "parameter": {"resolution": "1024x1024", "prompt": "A cat"},
                            }
                        ],
                    }
                ],
                "metadata": {},
            }
        )
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_sid",
            "llm_content": [
                {"role": "user", "part": [{"content_type": "text", "content_text": "Draw a cat"}]}
            ],
            "metadata": {"test": 123},
        }

        response = handle_image_generation(payload)
        self.validate_structure(response, "image")

        data = json.loads(response)
        self.assertEqual(data["metadata"].get("test"), 123)

    @patch("Backend.artificial_intelligence.tools.media.video_tools.load_video_tools")
    @patch("Backend.artificial_intelligence.service.video.get_ai_config")
    def test_video_generation_structure(self, mock_get_config, mock_load_tools):
        mock_tool = MagicMock()
        mock_tool.func.return_value = json.dumps(
            {
                "session_id": "test_sid",
                "error_code": 0,
                "status_info": "success",
                "llm_content": [
                    {
                        "role": "tool",
                        "interface_type": "video",
                        "sent_time_stamp": 123,
                        "part": [
                            {
                                "content_type": "video",
                                "content_url": "http://example.com/vid.mp4",
                                "parameter": {
                                    "resolution": "720P",
                                    "duration": 5,
                                    "status": "succeeded",
                                    "task_id": "hidden_id",
                                },
                            }
                        ],
                    }
                ],
                "metadata": {},
            }
        )
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_sid",
            "llm_content": [
                {
                    "role": "user",
                    "part": [
                        {"content_type": "text", "content_text": "A moving cat"},
                        {"content_type": "image", "content_url": "http://img"},
                    ],
                }
            ],
            "metadata": {"keep": "me"},
        }

        response = handle_video_generation(payload)
        self.validate_structure(response, "video")

        data = json.loads(response)
        self.assertEqual(data["metadata"].get("keep"), "me")
        # 验证 parameter 过滤
        params = data["llm_content"][0]["part"][0]["parameter"]
        self.assertNotIn("task_id", params)
        self.assertIn("resolution", params)

    @patch("Backend.artificial_intelligence.tools.media.music_tools.load_music_tools")
    @patch("Backend.artificial_intelligence.service.music.get_ai_config")
    def test_music_generation_structure(self, mock_get_config, mock_load_tools):
        mock_tool = MagicMock()
        mock_tool.func.return_value = json.dumps(
            {
                "session_id": "test_sid",
                "error_code": 0,
                "status_info": "success",
                "llm_content": [
                    {
                        "role": "tool",
                        "interface_type": "music",
                        "sent_time_stamp": 123,
                        "part": [
                            {
                                "content_type": "audio",
                                "content_url": "http://example.com/music.mp3",
                                "parameter": {"duration": 30, "music_style": "Jazz", "model": "V5"},
                            }
                        ],
                    }
                ],
                "metadata": {},
            }
        )
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_sid",
            "llm_content": [
                {"role": "user", "part": [{"content_type": "text", "content_text": "Jazz music"}]}
            ],
            "metadata": {"m": 1},
        }

        response = handle_music_generation(payload)
        self.validate_structure(response, "music")

        data = json.loads(response)
        params = data["llm_content"][0]["part"][0]["parameter"]
        self.assertNotIn("model", params)
        self.assertIn("music_style", params)

    @patch("Backend.artificial_intelligence.tools.media.speech_tools.load_speech_tools")
    @patch("Backend.artificial_intelligence.service.speech.get_ai_config")
    def test_speech_generation_structure(self, mock_get_config, mock_load_tools):
        mock_tool = MagicMock()
        mock_tool.func.return_value = json.dumps(
            {
                "session_id": "test_sid",
                "error_code": 0,
                "status_info": "success",
                "llm_content": [
                    {
                        "role": "tool",
                        "interface_type": "speech",
                        "sent_time_stamp": 123,
                        "part": [
                            {
                                "content_type": "audio",
                                "content_url": "http://example.com/speech.mp3",
                                "parameter": {
                                    "duration": 10,
                                    "speech_type": "female",
                                    "encoding": "mp3",
                                },
                            }
                        ],
                    }
                ],
                "metadata": {},
            }
        )
        mock_load_tools.return_value = [mock_tool]

        payload = {
            "session_id": "test_sid",
            "llm_content": [
                {"role": "user", "part": [{"content_type": "text", "content_text": "Hello"}]}
            ],
            "metadata": {"s": 2},
        }

        response = handle_speech_generation(payload)
        self.validate_structure(response, "speech")

        data = json.loads(response)
        params = data["llm_content"][0]["part"][0]["parameter"]
        self.assertNotIn("encoding", params)
        self.assertIn("speech_type", params)

    def test_integrated_structure(self):
        # 尝试直接 patch 模块中的名称
        with patch("Backend.artificial_intelligence.service.integrated.process_chat_request") as mock_process:
            mock_process.return_value = {
                "messages": [AIMessage(content="Chat response")],
                "session_id": "test_sid",
                "pending_history": [],
            }

            payload = {
                "session_id": "test_sid",
                "llm_content": [
                    {
                        "role": "user",
                        "part": [{"content_type": "text", "content_text": "Hi"}],
                    }
                ],
                "metadata": {"chat": "true"},
            }

            response = handle_integrated_entrance(payload)
            self.validate_structure(response, "integrated")

            data = json.loads(response)
            self.assertEqual(data["metadata"].get("chat"), "true")


if __name__ == "__main__":
    unittest.main()
