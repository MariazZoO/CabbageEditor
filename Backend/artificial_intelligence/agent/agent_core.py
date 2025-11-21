"""
向后兼容模块
保留旧的导入路径，实际功能已迁移到 executor.py
"""

from Backend.artificial_intelligence.agent.executor import (
    create_default_agent,
    run_agent,
    fallback_completion,
)

__all__ = [
    "create_default_agent",
    "run_agent",
    "fallback_completion",
]
