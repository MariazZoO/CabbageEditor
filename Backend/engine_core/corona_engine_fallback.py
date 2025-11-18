# -*- coding: utf-8 -*-
"""
CoronaEngine Python Fallback（OOP 版）
- 与 C++ 绑定导出的 API 形态对齐（顶层类：Geometry/Mechanics/Optics/Acoustics/Kinematics/ActorProfile/Actor/Camera/ImageEffects/Viewport/Environment/Scene）
"""
from __future__ import annotations
from typing import List, Optional
import warnings

# 一次性警告：仅在原生模块不可用时才会导入本模块
warnings.warn("[CoronaEngine][Fallback] 使用 Python fallback（未找到原生 CoronaEngine 模块），功能受限，仅用于开发/占位。",
              RuntimeWarning, stacklevel=2)


# ================================
# Geometry
# ================================
class Geometry:
    def __init__(self, model_path: str):
        print(f"[Fallback][Geometry.__init__] model_path={model_path}")
        self._model_path = model_path
        self._pos = [0.0, 0.0, 0.0]
        self._rot = [0.0, 0.0, 0.0]  # Euler ZYX
        self._scl = [1.0, 1.0, 1.0]

    def set_position(self, pos: List[float]):
        print(f"[Fallback][Geometry.set_position] pos={pos}")
        self._pos = list(pos)

    def set_rotation(self, euler: List[float]):
        print(f"[Fallback][Geometry.set_rotation] euler={euler}")
        self._rot = list(euler)

    def set_scale(self, scl: List[float]):
        print(f"[Fallback][Geometry.set_scale] scl={scl}")
        self._scl = list(scl)

    def get_position(self) -> List[float]:
        print("[Fallback][Geometry.get_position]")
        return list(self._pos)

    def get_rotation(self) -> List[float]:
        print("[Fallback][Geometry.get_rotation]")
        return list(self._rot)

    def get_scale(self) -> List[float]:
        print("[Fallback][Geometry.get_scale]")
        return list(self._scl)


# ================================
# Components
# ================================
class Mechanics:
    def __init__(self, geo: Geometry):
        print(f"[Fallback][Mechanics.__init__] geo={geo}")
        self._geo = geo


class Optics:
    def __init__(self, geo: Geometry):
        print(f"[Fallback][Optics.__init__] geo={geo}")
        self._geo = geo


class Acoustics:
    def __init__(self, geo: Geometry):
        print(f"[Fallback][Acoustics.__init__] geo={geo}")
        self._geo = geo
        self._volume = 1.0

    def set_volume(self, volume: float):
        print(f"[Fallback][Acoustics.set_volume] volume={volume}")
        self._volume = float(volume)

    def get_volume(self) -> float:
        print("[Fallback][Acoustics.get_volume]")
        return float(self._volume)


class Kinematics:
    def __init__(self, geo: Geometry):
        print(f"[Fallback][Kinematics.__init__] geo={geo}")
        self._geo = geo
        self._anim_index = 0
        self._time = 0.0
        self._playing = False
        self._speed = 1.0

    def set_animation(self, index: int):
        print(f"[Fallback][Kinematics.set_animation] index={index}")
        self._anim_index = int(index)
        self._time = 0.0

    def play_animation(self, speed: float = 1.0):
        print(f"[Fallback][Kinematics.play_animation] speed={speed}")
        self._playing = True
        self._speed = float(speed)

    def stop_animation(self):
        print("[Fallback][Kinematics.stop_animation]")
        self._playing = False

    def get_animation_index(self) -> int:
        print("[Fallback][Kinematics.get_animation_index]")
        return int(self._anim_index)

    def get_current_time(self) -> float:
        print("[Fallback][Kinematics.get_current_time]")
        return float(self._time)


# ================================
# Actor / Profile
# ================================
class ActorProfile:
    def __init__(self):
        print("[Fallback][ActorProfile.__init__]")
        self.optics: Optional[Optics] = None
        self.acoustics: Optional[Acoustics] = None
        self.mechanics: Optional[Mechanics] = None
        self.kinematics: Optional[Kinematics] = None
        self.geometry: Optional[Geometry] = None


class Actor:
    def __init__(self, path: str = ""):
        print(f"[Fallback][Actor.__init__] path={path}")
        # 兼容旧构造签名（path），但不再使用
        self._profiles: List[ActorProfile] = []
        self._active: Optional[ActorProfile] = None

    def add_profile(self, profile: ActorProfile) -> Optional[ActorProfile]:
        print(f"[Fallback][Actor.add_profile] profile={profile}")
        # 一致性校验：组件如存在必须共享同一几何体
        geo = profile.geometry
        if geo is None:
            print("[Fallback][Actor.add_profile] profile.geometry 不能为空")
            return None
        for comp in (profile.optics, profile.mechanics, profile.acoustics, profile.kinematics):
            if comp is not None and getattr(comp, "_geo", None) is not geo:
                print("[Fallback][Actor.add_profile] 组件与 profile.geometry 不一致，拒绝添加")
                return None
        self._profiles.append(profile)
        if self._active is None:
            self._active = profile
        return profile

    def remove_profile(self, profile: ActorProfile):
        print(f"[Fallback][Actor.remove_profile] profile={profile}")
        if profile in self._profiles:
            if self._active is profile:
                self._active = self._profiles[0] if len(self._profiles) > 1 else None
            self._profiles.remove(profile)

    def set_active_profile(self, profile: ActorProfile):
        print(f"[Fallback][Actor.set_active_profile] profile={profile}")
        if profile in self._profiles:
            self._active = profile
        else:
            print("[Fallback][Actor.set_active_profile] 指定的 profile 不属于该 Actor")

    def get_active_profile(self) -> Optional[ActorProfile]:
        print("[Fallback][Actor.get_active_profile]")
        return self._active

    def profile_count(self) -> int:
        print("[Fallback][Actor.profile_count]")
        return len(self._profiles)


# ================================
# Camera / ImageEffects / Viewport / Light
# ================================
class Camera:
    def __init__(self, position=None, forward=None, world_up=None, fov=None):
        print(f"[Fallback][Camera.__init__] position={position}, forward={forward}, world_up={world_up}, fov={fov}")
        self._position = list(position or [0.0, 0.0, 5.0])
        self._forward = list(forward or [0.0, 0.0, -1.0])
        self._world_up = list(world_up or [0.0, 1.0, 0.0])
        self._fov = float(fov) if fov is not None else 60.0
        self._surface = None

    def set(self, position, forward, world_up, fov):
        print(f"[Fallback][Camera.set] position={position}, forward={forward}, world_up={world_up}, fov={fov}")
        self._position = list(position)
        self._forward = list(forward)
        self._world_up = list(world_up)
        self._fov = float(fov)

    def set_surface(self, surface):
        print(f"[Fallback][Camera.set_surface] surface={surface}")
        self._surface = surface

    def get_position(self):
        print("[Fallback][Camera.get_position]")
        return list(self._position)

    def get_forward(self):
        print("[Fallback][Camera.get_forward]")
        return list(self._forward)

    def get_world_up(self):
        print("[Fallback][Camera.get_world_up]")
        return list(self._world_up)

    def get_fov(self):
        print("[Fallback][Camera.get_fov]")
        return float(self._fov)


class ImageEffects:
    def __init__(self):
        print("[Fallback][ImageEffects.__init__]")


class Viewport:
    def __init__(self, width: int = 0, height: int = 0, light_field: bool = False):
        print(f"[Fallback][Viewport.__init__] width={width}, height={height}, light_field={light_field}")
        self._w = int(width)
        self._h = int(height)
        self._lf = bool(light_field)
        self._camera: Optional[Camera] = None
        self._effects: Optional[ImageEffects] = None

    def set_camera(self, camera: Optional[Camera]):
        print(f"[Fallback][Viewport.set_camera] camera={camera}")
        self._camera = camera

    def get_camera(self) -> Optional[Camera]:
        print("[Fallback][Viewport.get_camera]")
        return self._camera

    def has_camera(self) -> bool:
        print("[Fallback][Viewport.has_camera]")
        return self._camera is not None

    def remove_camera(self):
        print("[Fallback][Viewport.remove_camera]")
        self._camera = None

    def set_image_effects(self, effects: Optional[ImageEffects]):
        print(f"[Fallback][Viewport.set_image_effects] effects={effects}")
        self._effects = effects

    def get_image_effects(self) -> Optional[ImageEffects]:
        print("[Fallback][Viewport.get_image_effects]")
        return self._effects

    def has_image_effects(self) -> bool:
        print("[Fallback][Viewport.has_image_effects]")
        return self._effects is not None

    def remove_image_effects(self):
        print("[Fallback][Viewport.remove_image_effects]")
        self._effects = None

    def set_size(self, width: int, height: int):
        print(f"[Fallback][Viewport.set_size] width={width}, height={height}")
        self._w, self._h = int(width), int(height)

    def set_viewport_rect(self, x: int, y: int, width: int, height: int):
        print(f"[Fallback][Viewport.set_viewport_rect] x={x}, y={y}, width={width}, height={height}")
        self._vp = (int(x), int(y), int(width), int(height))

    def pick_actor_at_pixel(self, x: int, y: int):
        print(f"[Fallback][Viewport.pick_actor_at_pixel] x={x}, y={y}")

    def save_screenshot(self, path: str):
        print(f"[Fallback][Viewport.save_screenshot] path={path}")


# ================================
# Environment / Scene
# ================================
class Environment:
    def __init__(self):
        print("[Fallback][Environment.__init__]")
        self._sun_dir = [0.0, -1.0, 0.0]
        self._floor_grid = False

    def set_sun_direction(self, direction: List[float]):
        print(f"[Fallback][Environment.set_sun_direction] direction={direction}")
        self._sun_dir = list(direction)

    def set_floor_grid(self, enabled: bool):
        print(f"[Fallback][Environment.set_floor_grid] enabled={enabled}")
        self._floor_grid = bool(enabled)


class Scene:
    def __init__(self, light_field: bool = False):
        print(f"[Fallback][Scene.__init__] light_field={light_field}")
        self._env: Optional[Environment] = None
        self._actors: List[Actor] = []
        self._viewports: List[Viewport] = []
        self._light_field = bool(light_field)

    # Environment
    def set_environment(self, env: Optional[Environment]):
        print(f"[Fallback][Scene.set_environment] env={env}")
        self._env = env

    def get_environment(self) -> Optional[Environment]:
        print("[Fallback][Scene.get_environment]")
        return self._env

    def has_environment(self) -> bool:
        print("[Fallback][Scene.has_environment]")
        return self._env is not None

    def remove_environment(self):
        print("[Fallback][Scene.remove_environment]")
        self._env = None

    # Actor
    def add_actor(self, actor: Actor):
        print(f"[Fallback][Scene.add_actor] actor={actor}")
        if actor not in self._actors:
            self._actors.append(actor)

    def remove_actor(self, actor: Actor):
        print(f"[Fallback][Scene.remove_actor] actor={actor}")
        if actor in self._actors:
            self._actors.remove(actor)

    def clear_actors(self):
        print("[Fallback][Scene.clear_actors]")
        self._actors.clear()

    def actor_count(self) -> int:
        print("[Fallback][Scene.actor_count]")
        return len(self._actors)

    def has_actor(self, actor: Actor) -> bool:
        print(f"[Fallback][Scene.has_actor] actor={actor}")
        return actor in self._actors

    # Viewport
    def add_viewport(self, vp: Viewport):
        print(f"[Fallback][Scene.add_viewport] viewport={vp}")
        if vp not in self._viewports:
            self._viewports.append(vp)

    def remove_viewport(self, vp: Viewport):
        print(f"[Fallback][Scene.remove_viewport] viewport={vp}")
        if vp in self._viewports:
            self._viewports.remove(vp)

    def clear_viewports(self):
        print("[Fallback][Scene.clear_viewports]")
        self._viewports.clear()

    def viewport_count(self) -> int:
        print("[Fallback][Scene.viewport_count]")
        return len(self._viewports)

    def has_viewport(self, vp: Viewport) -> bool:
        print(f"[Fallback][Scene.has_viewport] viewport={vp}")
        return vp in self._viewports


# ================================
# Facade（保持与旧加载器兼容）
# ================================
class CoronaEngine:
    Geometry = Geometry
    Mechanics = Mechanics
    Optics = Optics
    Acoustics = Acoustics
    Kinematics = Kinematics
    ActorProfile = ActorProfile
    Actor = Actor
    Camera = Camera
    ImageEffects = ImageEffects
    Viewport = Viewport
    Environment = Environment
    Scene = Scene
