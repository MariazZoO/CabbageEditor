from typing import Any, Dict, Optional, List
import os

from ..components.geometry import Geometry
from ..components.mechanics import Mechanics
from ..components.kinematics import Kinematics
from ..components.optics import Optics
from ..engine_import import load_corona_engine

CoronaEngine = load_corona_engine()


class Actor:
    """
    OOP API 包装：基于 CoronaEngine.Actor。
    - 构造可选传入模型路径：自动创建 Geometry + 默认组件，组装成 Profile 加入 Actor
    - move/rotate/scale 改为作用于 active profile 的 Geometry（不再调用原生的旧接口）
    """

    def __init__(self, path: Optional[str] = None):
        if CoronaEngine is None:
            raise RuntimeError("CoronaEngine 未初始化")

        ActorCtor = getattr(CoronaEngine, 'Actor', None)
        if ActorCtor is None:
            raise RuntimeError("CoronaEngine 未提供 Actor 构造器")

        self.engine_obj = ActorCtor()
        self.path = path or ""
        self.name = os.path.basename(path) if path else "Actor"

        # 若提供了模型路径，则创建默认 Profile
        if path:
            if not os.path.exists(path):
                raise FileNotFoundError(f"模型文件不存在: {path}")

            ActorProfile = getattr(CoronaEngine, 'ActorProfile', None)
            if ActorProfile is None:
                raise RuntimeError("CoronaEngine 未提供 ActorProfile 类型")

            # 使用包装类创建组件
            # 重要：必须保持对包装对象的引用，否则析构时会从 SharedDataHub 中移除
            self._geometry = Geometry(path)
            self._optics = Optics(self._geometry)
            # 可选组件（按需创建）
            # self._mechanics = Mechanics(self._geometry)
            # self._kinematics = Kinematics(self._geometry)
            # self._acoustics = Acoustics(self._geometry)

            prof = ActorProfile()
            prof.geometry = self._geometry.engine_obj
            prof.optics = self._optics.engine_obj
            # prof.mechanics = self._mechanics.engine_obj if hasattr(self, '_mechanics') else None
            # prof.kinematics = self._kinematics.engine_obj if hasattr(self, '_kinematics') else None
            # prof.acoustics = self._acoustics.engine_obj if hasattr(self, '_acoustics') else None

            stored = self.engine_obj.add_profile(prof)
            if stored is None:
                raise RuntimeError("无法向 Actor 添加默认 Profile（几何/组件不一致）")
            self.engine_obj.set_active_profile(stored)

    # 兼容编辑器的变换操作：直接作用于几何体
    def scale(self, v: List[float]):
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        self._geometry.set_scale(v)

    def move(self, v: List[float]):
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        pos = self._geometry.get_position()
        new_pos = [pos[0] + v[0], pos[1] + v[1], pos[2] + v[2]]
        print(f"[Actor.move] {self.name}: {pos} → {new_pos}")
        self._geometry.set_position(new_pos)

    def rotate(self, euler: List[float]):
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        rot = self._geometry.get_rotation()
        self._geometry.set_rotation([rot[0] + euler[0], rot[1] + euler[1], rot[2] + euler[2]])

    def set_position(self, position: List[float]):
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        self._geometry.set_position(position)

    def get_position(self) -> List[float]:
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        return self._geometry.get_position()

    def set_rotation(self, euler: List[float]):
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        self._geometry.set_rotation(euler)

    def get_rotation(self) -> List[float]:
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        return self._geometry.get_rotation()

    def set_scale(self, scale: List[float]):
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        self._geometry.set_scale(scale)

    def get_scale(self) -> List[float]:
        if not hasattr(self, '_geometry'):
            raise RuntimeError("当前 Actor 没有 Geometry")
        return self._geometry.get_scale()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "engine_obj": self.engine_obj,
        }

    def __repr__(self):
        return f"<Actor name={self.name} path={self.path}>"
