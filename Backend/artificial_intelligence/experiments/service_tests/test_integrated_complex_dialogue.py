import unittest
import json
from unittest.mock import patch
import sys
import os
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# 添加项目根目录到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

# 假设导入路径已正确设置
from Backend.artificial_intelligence.service.integrated import (
    handle_integrated_entrance,
)


class TestIntegratedComplexDialogue(unittest.TestCase):

    @patch("Backend.artificial_intelligence.service.integrated.process_chat_request")
    def test_complex_dialogue_structure(self, mock_process):
        # --- 1. 构造符合新协议的 Mock 数据 ---

        tool_content = {
            "session_id": "test_sess_002",
            "error_code": 0,
            "status_info": "ok",
            "llm_content": [
                {
                    "role": "tool",
                    "part": [
                        {
                            "content_type": "image",
                            "content_url": "http://gen.com/art.jpg",
                            "parameter": {"resolution": "1:1"},
                        }
                    ],
                }
            ],
        }

        mock_messages = [
            # 第一轮：用户提问
            HumanMessage(content="帮我生成一张猫的图片"),
            # 第二轮：AI 回复（第一次输出）
            AIMessage(content="好的，正在为您生成..."),
            # 第三轮：工具输出（生成了图片）
            # 注意：content 是 json.dumps 后的字符串
            ToolMessage(
                content=json.dumps(tool_content), tool_call_id="call_123", name="generate_image"
            ),
            # 第四轮：AI 回复（对图片的评论）
            # 我们的逻辑应该把上面的 Tool 图片“吸附”到这条消息上
            AIMessage(content="图片生成好了，你看怎么样？"),
        ]

        mock_process.return_value = {
            "messages": mock_messages,
            "session_id": "test_sid",
            "pending_history": [],
        }

        # --- 2. 构造请求 Payload ---
        payload = {
            "session_id": "test_sid",
            "llm_content": [
                {
                    "role": "user",
                    "part": [{"content_type": "text", "content_text": "帮我生成一张猫的图片"}],
                }
            ],
            "metadata": {"test": "complex"},
        }

        # --- 3. 执行测试 ---
        response = handle_integrated_entrance(payload)
        data = json.loads(response)

        # --- 4. 验证断言 ---

        print("\n=== Integrated Response JSON ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        llm_content = data["llm_content"]

        # 验证输出了两条 Assistant 消息（全量输出）
        self.assertEqual(len(llm_content), 2)

        # [验证第一条消息]：纯文本
        msg1 = llm_content[0]
        self.assertEqual(msg1["role"], "assistant")
        self.assertEqual(msg1["part"][0]["content_text"], "好的，正在为您生成...")

        # [验证第二条消息]：核心验证点 —— 媒体吸附
        # 这条消息应该包含两个 part：[0]是文本(来自Assistant)，[1]是图片(来自Tool)
        msg2 = llm_content[1]
        self.assertEqual(msg2["role"], "assistant")
        self.assertEqual(len(msg2["part"]), 2, "第二条消息应该包含图片和文本两个部分")

        # 检查图片部分 (吸附成功)
        part_image = msg2["part"][1]
        self.assertEqual(part_image["content_type"], "image")
        self.assertEqual(part_image["content_url"], "http://gen.com/art.jpg")
        self.assertEqual(part_image["parameter"]["resolution"], "1:1")

        # 检查文本部分
        part_text = msg2["part"][0]
        self.assertEqual(part_text["content_type"], "text")
        self.assertEqual(part_text["content_text"], "图片生成好了，你看怎么样？")


if __name__ == "__main__":
    unittest.main()
