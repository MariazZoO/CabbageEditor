"""Blockly 脚本执行器。"""
import importlib.util
from typing import Optional
from PySide6.QtCore import QCoreApplication


class ScriptRunner:
    """管理 runScript.py 的加载和执行。"""

    def __init__(self, app: QCoreApplication):
        self.app = app

    def load_and_run(self) -> bool:
        """加载并执行 runScript.py。

        Returns:
            bool: 成功返回 True，无脚本或失败返回 False
        """
        spec = importlib.util.find_spec("runScript")
        if spec is None:
            return False

        try:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.run()
            return True
        except Exception as e:
            print(f"✗ runScript.run 执行失败: {e}")
            return False
        finally:
            self.app.processEvents()
