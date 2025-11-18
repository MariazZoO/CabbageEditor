from typing import List, Any, Optional
from ..components.geometry import Geometry
from .actor import Actor
from .camera import Camera
from .environment import Environment
from .viewport import Viewport

from ..engine_import import load_corona_engine

CoronaEngine = load_corona_engine()


class Scene:
    """
    场景包装类：仅管理对象引用，生命周期由外部管理。
    采用 OOP API：引擎 Scene 仅支持 Environment/Actor/Viewport 管理。
    """

    def __init__(self, name: str = "Scene"):
        self.name = name

        # 创建引擎场景对象（OOP API）
        if CoronaEngine is None:
            raise RuntimeError("CoronaEngine 未初始化")
        SceneCtor = getattr(CoronaEngine, 'Scene', None)
        if SceneCtor is None:
            raise RuntimeError("CoronaEngine 未提供 Scene 构造器")
        self.engine_scene = SceneCtor()

        # 引用列表（Python 层）
        self._actors: List[Actor] = []
        self._viewports: List[Viewport] = []

        # 环境对象（Python 层）
        self._environment: Optional[Environment] = None

    # Environment
    def set_environment(self, environment: Environment) -> None:
        self._environment = environment
        if hasattr(self.engine_scene, 'set_environment'):
            self.engine_scene.set_environment(
                environment.engine_obj if hasattr(environment, 'engine_obj') else environment)

    def get_environment(self) -> Optional[Environment]:
        return self._environment

    # Actor 管理
    def add_actor(self, actor: Actor) -> None:
        if actor in self._actors:
            return
        self._actors.append(actor)
        if hasattr(self.engine_scene, 'add_actor'):
            self.engine_scene.add_actor(actor.engine_obj)

    def remove_actor(self, actor: Actor) -> bool:
        if actor not in self._actors:
            return False
        self._actors.remove(actor)
        if hasattr(self.engine_scene, 'remove_actor'):
            self.engine_scene.remove_actor(actor.engine_obj)
        return True

    def clear_actors(self) -> None:
        for actor in self._actors.copy():
            self.remove_actor(actor)

    # 视口管理
    def add_viewport(self, viewport: Viewport) -> None:
        if viewport in self._viewports:
            return
        self._viewports.append(viewport)
        self.engine_scene.add_viewport(getattr(viewport, 'engine_obj', viewport))

    def remove_viewport(self, viewport: Viewport) -> bool:
        if viewport not in self._viewports:
            return False
        self._viewports.remove(viewport)
        self.engine_scene.remove_viewport(getattr(viewport, 'engine_obj', viewport))
        return True

    def clear_viewports(self) -> None:
        for vp in self._viewports.copy():
            self.remove_viewport(vp)

    def get_viewports(self) -> List[Viewport]:
        return self._viewports.copy()

    # 查询
    def get_actors(self) -> List[Actor]:
        return self._actors.copy()

    def get_actor(self, actor_name: str) -> Optional[Actor]:
        for actor in self._actors:
            if actor.name == actor_name:
                return actor
        return None
