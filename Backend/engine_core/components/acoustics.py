from typing import Any, Dict
from ..engine_import import load_corona_engine
from .geometry import Geometry

CoronaEngine = load_corona_engine()


class Acoustics:
    def __init__(self, geometry: Geometry, name: str = 'Acoustics'):
        if CoronaEngine is None:
            raise RuntimeError('CoronaEngine 未初始化')
        AcousticsCtor = getattr(CoronaEngine, 'Acoustics', None)
        if AcousticsCtor is None:
            raise RuntimeError('CoronaEngine 未提供 Acoustics 构造器')
        geo_obj = geometry.engine_obj if hasattr(geometry, 'engine_obj') else geometry
        self.engine_obj = AcousticsCtor(geo_obj)
        self.name = name
        self.geometry = geometry

    def set_volume(self, volume: float):
        self.engine_obj.set_volume(volume)

    def get_volume(self) -> float:
        return self.engine_obj.get_volume()

    def to_dict(self) -> Dict[str, Any]:
        return {'name': self.name, 'engine_obj': self.engine_obj}

    def __repr__(self):
        return f'Acoustics(name={self.name})'
