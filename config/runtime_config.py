"""
运行时配置
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    """运行时配置"""
    enable_gpu: bool = False
    log_level: str = "INFO"
    debug_mode: bool = False
    InnerAgentWorkFlow: bool = False

