from typing import Any, Dict, List

from ..engine_import import load_corona_engine

CoronaEngine = load_corona_engine()


class Environment:
    """
    Environment 包装类：环境设置（太阳方向、地面网格等）

    使用方式：
        env = Environment()
        env.set_sun_direction([1.0, -1.0, 0.0])
        scene.set_environment(env)
    """

    def __init__(self, name: str = "Environment"):
        """
        创建 Environment 对象

        Args:
            name: 环境名称
        """
        if CoronaEngine is None:
            raise RuntimeError("CoronaEngine 未初始化")

        EnvironmentCtor = getattr(CoronaEngine, 'Environment', None)
        if EnvironmentCtor is None:
            raise RuntimeError("CoronaEngine 未提供 Environment 构造器")

        self.engine_obj = EnvironmentCtor()
        self.name = name

    def set_sun_direction(self, direction: List[float]):
        """设置太阳/主光源方向"""
        try:
            self.engine_obj.set_sun_direction(direction)
        except Exception as e:
            raise RuntimeError(f"Environment.set_sun_direction 失败: {e}") from e

    def set_floor_grid(self, enabled: bool):
        """启用或禁用地面网格"""
        try:
            self.engine_obj.set_floor_grid(enabled)
        except Exception as e:
            raise RuntimeError(f"Environment.set_floor_grid 失败: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            'name': self.name,
            'engine_obj': self.engine_obj,
        }

    def __repr__(self):
        return f"Environment(name={self.name})"
