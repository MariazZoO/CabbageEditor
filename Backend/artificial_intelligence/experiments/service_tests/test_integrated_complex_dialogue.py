import unittest
import json
from unittest.mock import MagicMock, patch
import sys
import os
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from Backend.artificial_intelligence.service.integrated import (
    handle_integrated_entrance,
)


class TestIntegratedComplexDialogue(unittest.TestCase):

    @patch("Backend.artificial_intelligence.service.integrated.process_chat_request")
    def test_complex_dialogue_structure(self, mock_process):
        # 模拟多轮对话历史
        # 1. 用户: "帮我生成一张猫的图片"
        # 2. 助手: "好的，正在为您生成..."
        # 3. 工具: 返回图片 URL (JSON Envelope)
        # 4. 助手: "图片生成好了，你看怎么样？"

        tool_output_envelope = {
            "session_id": "test_sid",
            "error_code": 0,
            "status_info": "success",
            "llm_content": [
                {
                    "role": "tool",
                    "interface_type": "image",
                    "sent_time_stamp": 1234567890,
                    "part": [
                        {
                            "content_type": "image",
                            "content_url": "http://example.com/cat.png",
                            "parameter": {"prompt": "cat"},
                        }
                    ],
                }
            ],
            "metadata": {},
        }

        mock_messages = [
            HumanMessage(content="帮我生成一张猫的图片"),
            AIMessage(content="好的，正在为您生成..."),
            ToolMessage(
                content=json.dumps(tool_output_envelope), tool_call_id="call_123"
            ),
            AIMessage(content="图片生成好了，你看怎么样？"),
        ]

        mock_process.return_value = {
            "messages": mock_messages,
            "session_id": "test_sid",
            "pending_history": [],
        }

        payload = {
            "session_id": "test_sid",
            "llm_content": [
                {
                    "role": "user",
                    "part": [
                        {"content_type": "text", "content_text": "帮我生成一张猫的图片"}
                    ],
                }
            ],
            "metadata": {"test": "complex"},
        }

        response = handle_integrated_entrance(payload)
        data = json.loads(response)

        # 验证顶层结构
        self.assertEqual(data["session_id"], "test_sid")
        self.assertEqual(data["error_code"], 0)
        self.assertEqual(data["metadata"]["test"], "complex")

        llm_content = data["llm_content"]
        self.assertIsInstance(llm_content, list)

        # 验证消息数量
        # 1. HumanMessage -> role: user
        # 2. AIMessage -> role: assistant
        # 3. ToolMessage -> role: tool (from envelope)
        # 4. AIMessage -> role: assistant
        self.assertEqual(len(llm_content), 4)

        # 验证第一条：用户消息
        self.assertEqual(llm_content[0]["role"], "user")
        self.assertEqual(
            llm_content[0]["part"][0]["content_text"], "帮我生成一张猫的图片"
        )

        # 验证第二条：助手消息
        self.assertEqual(llm_content[1]["role"], "assistant")
        self.assertEqual(
            llm_content[1]["part"][0]["content_text"], "好的，正在为您生成..."
        )

        # 验证第三条：工具消息 (解析后的)
        self.assertEqual(llm_content[2]["role"], "tool")
        self.assertEqual(llm_content[2]["interface_type"], "image")
        self.assertEqual(llm_content[2]["part"][0]["content_type"], "image")
        self.assertEqual(
            llm_content[2]["part"][0]["content_url"], "http://example.com/cat.png"
        )

        # 验证第四条：助手消息
        self.assertEqual(llm_content[3]["role"], "assistant")
        self.assertEqual(
            llm_content[3]["part"][0]["content_text"], "图片生成好了，你看怎么样？"
        )

        print("\n=== Integrated Response JSON ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print("================================")


if __name__ == "__main__":
    unittest.main()
