import unittest
import json
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from Backend.artificial_intelligence.service.text import handle_text_generation
from Backend.artificial_intelligence.service.image import handle_image_generation
from Backend.artificial_intelligence.service.video import handle_video_generation
from Backend.artificial_intelligence.service.music import handle_music_generation
from Backend.artificial_intelligence.service.speech import handle_speech_generation


class TestBusinessFlow(unittest.TestCase):
    """
    Full-process business flow tests.
    These tests verify the entire chain from Service Entry -> Tool Loading -> Tool Execution (Mocked Client) -> \
Response Adapter -> JSON Envelope.
    They ensure that the business logic (parameter parsing, validation, response formatting) works correctly.
    """

    def setUp(self):
        # Common mock setup if needed
        pass

    @patch("Backend.artificial_intelligence.tools.text.get_chat_model")
    @patch("Backend.artificial_intelligence.service.text.get_ai_config")
    def test_text_generation_flow(self, mock_get_config, mock_get_chat_model):
        """Test the full flow of text generation (Product Text)"""
        # 1. Mock Config
        mock_config = MagicMock()
        mock_config.providers = {"doubao": MagicMock()}
        mock_get_config.return_value = mock_config

        # 2. Mock LLM
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content="This is a generated product description."
        )
        mock_get_chat_model.return_value = mock_llm

        # 3. Prepare Request Payload
        payload = {
            "session_id": "test_session_text",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "text",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "Product: Smart Watch. Features: Waterproof.",
                            "parameter": {
                                "text_type": "product",
                                "style": "Professional",
                                "length": "Medium",
                            },
                        }
                    ],
                }
            ],
        }

        # 4. Execute Service
        response_str = handle_text_generation(payload)
        response = json.loads(response_str)

        # 5. Verify Response Structure & Content
        self.assertEqual(response["error_code"], 0)
        self.assertEqual(response["session_id"], "test_session_text")

        llm_content = response["llm_content"][0]
        self.assertEqual(
            llm_content["role"], "assistant"
        )  # Service returns assistant role
        self.assertEqual(llm_content["interface_type"], "text")

        part = llm_content["part"][0]
        self.assertEqual(part["content_type"], "text")
        self.assertEqual(
            part["content_text"], "This is a generated product description."
        )
        self.assertEqual(part["parameter"]["text_type"], "product_text")

        # 6. Verify LLM was called with correct prompt (indirectly)
        mock_llm.invoke.assert_called_once()
        args, _ = mock_llm.invoke.call_args
        messages = args[0]
        self.assertTrue(any("Smart Watch" in m.content for m in messages))

    @patch("Backend.artificial_intelligence.tools.media.image_tools.LingyaImageClient")
    @patch("Backend.artificial_intelligence.service.image.get_ai_config")
    def test_image_generation_flow(self, mock_get_config, mock_client_cls):
        """Test the full flow of image generation"""
        # 1. Mock Config
        mock_config = MagicMock()
        mock_config.media.image.enable = True
        mock_config.media.image.provider = "lingya"
        mock_config.media.image.model = "v1"
        mock_provider = MagicMock(api_key="key", base_url="url")
        mock_provider.name = "lingya"
        mock_config.providers = {"lingya": mock_provider}
        mock_get_config.return_value = mock_config

        # 2. Mock Client
        mock_client = mock_client_cls.return_value
        mock_client.generate.return_value = ("http://mock.url/image.png", "image/png")

        # 3. Prepare Request
        payload = {
            "session_id": "test_session_image",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "image",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "A cute cat",
                            "parameter": {
                                "resolution": "16:9"
                            },  # Service maps resolution to aspect_ratio
                        }
                    ],
                }
            ],
        }

        # 4. Execute
        response_str = handle_image_generation(payload)
        response = json.loads(response_str)

        if response["error_code"] != 0:
            print(f"\nImage Generation Error: {response.get('status_info')}")

        # 5. Verify
        self.assertEqual(response["error_code"], 0)
        part = response["llm_content"][0]["part"][0]
        self.assertEqual(part["content_url"], "http://mock.url/image.png")
        self.assertEqual(part["content_text"], "A cute cat")
        self.assertEqual(part["parameter"]["resolution"], "16:9")

        # 6. Verify Client Call
        mock_client.generate.assert_called_with(
            prompt="A cute cat",
            aspect_ratio="16:9",
            store=None,
            product_url=None,
            scene_url=None,
        )

    @patch(
        "Backend.artificial_intelligence.tools.media.video_tools.DashScopeVideoClient"
    )
    @patch("Backend.artificial_intelligence.service.video.get_ai_config")
    def test_video_generation_flow(self, mock_get_config, mock_client_cls):
        """Test the full flow of video generation"""
        mock_config = MagicMock()
        mock_config.media.video.enable = True
        mock_config.media.video.provider = "aliyun"
        mock_config.media.video.model = "wan2.1"
        mock_provider = MagicMock(api_key="key")
        mock_provider.name = "aliyun"  # Fix serialization
        mock_config.providers = {"aliyun": mock_provider}
        mock_get_config.return_value = mock_config

        mock_client = mock_client_cls.return_value
        mock_client.model = "wan2.1"  # Fix serialization
        mock_client.generate_video_from_image.return_value = {
            "output": {
                "video_url": "http://mock.url/video.mp4",
                "actual_prompt": "expanded prompt",
            }
        }

        payload = {
            "session_id": "test_session_video",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "video",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "Moving cat",
                            "parameter": {"resolution": "720P"},
                        },
                        {
                            "content_type": "image",
                            "content_url": "http://img.com/src.png",
                        },
                    ],
                }
            ],
        }

        response_str = handle_video_generation(payload)
        response = json.loads(response_str)

        self.assertEqual(response["error_code"], 0)
        part = response["llm_content"][0]["part"][0]
        self.assertEqual(part["content_url"], "http://mock.url/video.mp4")
        self.assertEqual(part["content_text"], "Moving cat")

        mock_client.generate_video_from_image.assert_called()

    @patch("Backend.artificial_intelligence.tools.media.music_tools.SunoMusicClient")
    @patch("Backend.artificial_intelligence.service.music.get_ai_config")
    def test_music_generation_flow(self, mock_get_config, mock_client_cls):
        """Test music generation flow (Suno)"""
        mock_config = MagicMock()
        mock_config.music.api_key = "suno_key"
        mock_config.music.base_url = "https://suno.api"
        mock_get_config.return_value = mock_config

        # Mock Client
        mock_client = mock_client_cls.return_value
        mock_client.generate_music.return_value = [
            {
                "audio_url": "http://music.mp3",
                "duration": 30,
                "title": "Song",
                "model": "V5",
            }
        ]

        payload = {
            "session_id": "test_session_music",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "music",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "Jazz",
                            "parameter": {"style": "Jazz", "wait": True},
                        }
                    ],
                }
            ],
        }

        response_str = handle_music_generation(payload)
        response = json.loads(response_str)

        if response["error_code"] != 0:
            print(f"\nMusic Generation Error: {response.get('status_info')}")

        self.assertEqual(response["error_code"], 0)
        part = response["llm_content"][0]["part"][0]
        self.assertEqual(part["content_url"], "http://music.mp3")
        self.assertEqual(part["content_text"], "Song")
        self.assertEqual(part["parameter"]["music_style"], "Jazz")

    @patch(
        "Backend.artificial_intelligence.tools.media.speech_tools.create_speech_client"
    )
    @patch("Backend.artificial_intelligence.service.speech.get_ai_config")
    def test_speech_generation_flow(self, mock_get_config, mock_create_client):
        """Test speech generation flow (TTS)"""
        mock_config = MagicMock()
        mock_config.tts.appid = "app_123"
        mock_config.tts.token = "token_123"
        mock_get_config.return_value = mock_config

        mock_client = mock_create_client.return_value
        mock_client.synthesize_async.return_value = {
            "audio_url": "http://tts.mp3",
            "duration": 5.5,
            "req_text_length": 10,
        }

        payload = {
            "session_id": "test_session_speech",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "speech",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "Hello World",
                            "parameter": {"voice_type": "female"},
                        }
                    ],
                }
            ],
        }

        response_str = handle_speech_generation(payload)
        response = json.loads(response_str)

        self.assertEqual(response["error_code"], 0)
        part = response["llm_content"][0]["part"][0]
        self.assertEqual(part["content_url"], "http://tts.mp3")
        self.assertEqual(part["content_text"], "Hello World")
        self.assertEqual(part["parameter"]["speech_type"], "female")

    @patch("Backend.artificial_intelligence.tools.media.image_tools.LingyaImageClient")
    @patch("Backend.artificial_intelligence.service.image.get_ai_config")
    def test_image_generation_with_images_flow(self, mock_get_config, mock_client_cls):
        """Test the full flow of image generation with multiple input images (Image-to-Image)"""
        # 1. Mock Config
        mock_config = MagicMock()
        mock_config.media.image.enable = True
        mock_config.media.image.provider = "lingya"
        mock_config.media.image.model = "v1"
        mock_provider = MagicMock(api_key="key", base_url="url")
        mock_provider.name = "lingya"
        mock_config.providers = {"lingya": mock_provider}
        mock_get_config.return_value = mock_config

        # 2. Mock Client
        mock_client = mock_client_cls.return_value
        mock_client.generate.return_value = ("http://mock.url/result.png", "image/png")

        # 3. Prepare Request with multiple images
        payload = {
            "session_id": "test_session_image_i2i",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "image",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "Combine these images",
                        },
                        {
                            "content_type": "image",
                            "content_url": "http://img.com/product.png",
                            "content_text": "This is the product image",
                        },
                        {
                            "content_type": "image",
                            "content_url": "http://img.com/scene.png",
                            "content_text": "This is the scene background",
                        },
                    ],
                }
            ],
        }

        # 4. Execute
        response_str = handle_image_generation(payload)
        response = json.loads(response_str)

        if response["error_code"] != 0:
            print(f"\nImage Generation Error: {response.get('status_info')}")

        # 5. Verify
        self.assertEqual(response["error_code"], 0)
        part = response["llm_content"][0]["part"][0]
        self.assertEqual(part["content_url"], "http://mock.url/result.png")
        self.assertEqual(part["content_text"], "Combine these images")

        # 6. Verify Client Call - Check if product_url and scene_url are correctly extracted
        mock_client.generate.assert_called_with(
            prompt="Combine these images",
            aspect_ratio="1:1",  # Default
            store=None,
            product_url="http://img.com/product.png",
            scene_url="http://img.com/scene.png",
        )


if __name__ == "__main__":
    unittest.main()
