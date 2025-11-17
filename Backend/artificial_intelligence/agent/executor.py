from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.messages import BaseMessage

from Backend.artificial_intelligence.agent.factory import create_default_agent


def run_agent(messages: List[BaseMessage]) -> Dict[str, Any]:
    """
    运行 agent，接受标准的 LangChain BaseMessage 列表。

    Args:
        messages: LangChain BaseMessage 列表（HumanMessage, AIMessage 等）

    Returns:
        Agent 执行结果
    """
    agent = create_default_agent()
    return agent.invoke({"messages": messages})


__all__ = ["run_agent"]
