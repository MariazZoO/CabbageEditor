from typing import Any, TypeVar, Callable, Dict
import os
import weakref
import logging

from .engine_import import load_corona_engine

logger = logging.getLogger(__name__)

CoronaEngine = load_corona_engine()
if CoronaEngine is None:
    logger.warning("未找到 CoronaEngine (需要 -DBUILD_CORONA_EDITOR=ON)")
else:
    logger.info("使用 CoronaEngine / CoronaEngineFallback")

from .entities.actor import Actor
from .entities.camera import Camera

T = TypeVar('T')


class EngineObjectFactory:
    """引擎对象工厂，负责创建和缓存引擎对象"""

    _actor_cache: Dict[str, Actor] = weakref.WeakValueDictionary()
    _camera_cache: Dict[str, Camera] = weakref.WeakValueDictionary()

    @staticmethod
    def _ensure_engine() -> None:
        """确保引擎已初始化"""
        if CoronaEngine is None:
            raise RuntimeError("CoronaEngine 未初始化，请检查编译配置")

    @classmethod
    def _get_or_create(
            cls,
            cache: Dict[str, T],
            key: str,
            factory: Callable[[], T]
    ) -> T:
        """
        通用缓存获取或创建逻辑

        Args:
            cache: 缓存字典
            key: 缓存键
            factory: 创建对象的工厂函数

        Returns:
            缓存或新创建的对象
        """
        if key in cache:
            return cache[key]

        obj = factory()
        cache[key] = obj
        return obj

    @staticmethod
    def create_scene(light_field: bool = False) -> Any:
        """
        创建场景对象

        Args:
            light_field: 是否使用光场，默认 False

        Returns:
            引擎场景对象
        """
        EngineObjectFactory._ensure_engine()

        SceneCtor = getattr(CoronaEngine, 'Scene', None)
        if SceneCtor is None:
            raise RuntimeError("CoronaEngine 未提供 Scene 构造器")

        return SceneCtor(light_field=light_field)

    @classmethod
    def create_actor(cls, obj_path: str, use_cache: bool = True) -> Actor:
        """
        创建 Actor 对象

        Args:
            obj_path: 模型文件路径
            use_cache: 是否使用缓存，默认 True

        Returns:
            Actor 包装对象
        """
        cls._ensure_engine()

        if not os.path.exists(obj_path):
            raise FileNotFoundError(f"角色文件不存在: {obj_path}")

        cache_key = os.path.basename(obj_path)

        if not use_cache:
            return cls._create_actor_internal(obj_path, cache_key)

        return cls._get_or_create(
            cls._actor_cache,
            cache_key,
            lambda: cls._create_actor_internal(obj_path, cache_key)
        )

    @classmethod
    def _create_actor_internal(cls, obj_path: str, name: str) -> Actor:
        """内部方法：实际创建 Actor 对象（使用 OOP API）"""
        try:
            wrapper = Actor(obj_path)
            wrapper.name = name
            return wrapper
        except Exception as e:
            raise RuntimeError(f"无法创建 Actor: {e}") from e

    @classmethod
    def create_camera(cls, name: str = "MainCamera", use_cache: bool = True) -> Camera:
        """
        创建 Camera 对象

        Args:
            name: 相机名称，用于缓存和标识
            use_cache: 是否使用缓存，默认 True

        Returns:
            Camera 包装对象
        """
        cls._ensure_engine()

        if not use_cache:
            return cls._create_camera_internal(name)

        return cls._get_or_create(
            cls._camera_cache,
            name,
            lambda: cls._create_camera_internal(name)
        )

    @classmethod
    def _create_camera_internal(cls, name: str) -> Camera:
        """内部方法：实际创建 Camera 对象（使用 OOP API）"""
        try:
            return Camera(name=name)
        except Exception as e:
            raise RuntimeError(f"无法创建 Camera: {e}") from e

    @classmethod
    def clear_cache(cls, cache_type: str = "all") -> None:
        """
        清空缓存

        Args:
            cache_type: 缓存类型 ("actor", "camera", "all")
        """
        if cache_type in ("actor", "all"):
            cls._actor_cache.clear()
        if cache_type in ("camera", "all"):
            cls._camera_cache.clear()
