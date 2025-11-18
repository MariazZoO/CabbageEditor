from typing import Any, Dict, List, Optional

from ..engine_import import load_corona_engine

CoronaEngine = load_corona_engine()


class Camera:
    """
    OOP 相机包装：统一通过 set(...) 推送到引擎；包装层提供单项 setter 并维护本地缓存。
    """

    def __init__(self, position: Optional[List[float]] = None, forward: Optional[List[float]] = None,
                 world_up: Optional[List[float]] = None, fov: Optional[float] = None, name: str = "Camera"):
        if CoronaEngine is None:
            raise RuntimeError("CoronaEngine 未初始化")

        CameraCtor = getattr(CoronaEngine, 'Camera', None)
        if CameraCtor is None:
            raise RuntimeError("CoronaEngine 未提供 Camera 构造器")

        if position is not None and forward is not None and world_up is not None and fov is not None:
            self.engine_obj = CameraCtor(position, forward, world_up, fov)
            self._pos = list(position)
            self._fwd = list(forward)
            self._up = list(world_up)
            self._fov = float(fov)
        else:
            self.engine_obj = CameraCtor()
            self._pos = self.engine_obj.get_position()
            self._fwd = self.engine_obj.get_forward()
            self._up = self.engine_obj.get_world_up()
            self._fov = self.engine_obj.get_fov()

        self.name = name

    # 单项 setter：更新缓存并统一调用 set
    def _flush(self):
        self.engine_obj.set(self._pos, self._fwd, self._up, self._fov)

    def set_position(self, position: List[float]):
        self._pos = list(position)
        self._flush()

    def get_position(self) -> List[float]:
        return self.engine_obj.get_position()

    def set_forward(self, forward: List[float]):
        self._fwd = list(forward)
        self._flush()

    def get_forward(self) -> List[float]:
        return self.engine_obj.get_forward()

    def set_world_up(self, world_up: List[float]):
        self._up = list(world_up)
        self._flush()

    def get_world_up(self) -> List[float]:
        return self.engine_obj.get_world_up()

    def set_fov(self, fov: float):
        self._fov = float(fov)
        self._flush()

    def get_fov(self) -> float:
        return self.engine_obj.get_fov()

    # 新接口直通
    def set(self, position: List[float], forward: List[float], world_up: List[float], fov: float):
        self._pos, self._fwd, self._up, self._fov = list(position), list(forward), list(world_up), float(fov)
        self.engine_obj.set(self._pos, self._fwd, self._up, self._fov)

    def set_surface(self, surface: int):
        self.engine_obj.set_surface(surface)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'engine_obj': self.engine_obj,
        }

    def __repr__(self):
        return f"Camera(name={self.name})"
