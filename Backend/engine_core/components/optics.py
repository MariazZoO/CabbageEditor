from typing import Any, Dict
from ..engine_import import load_corona_engine
from .geometry import Geometry

CoronaEngine = load_corona_engine()


class Optics:
    def __init__(self, geometry: Geometry, name: str = 'Optics'):
        if CoronaEngine is None:
            raise RuntimeError('CoronaEngine 未初始化')
        OpticsCtor = getattr(CoronaEngine, 'Optics', None)
        if OpticsCtor is None:
            raise RuntimeError('CoronaEngine 未提供 Optics 构造器')
        geo_obj = geometry.engine_obj if hasattr(geometry, 'engine_obj') else geometry
        self.engine_obj = OpticsCtor(geo_obj)
        self.name = name
        self.geometry = geometry

    def to_dict(self) -> Dict[str, Any]:
        return {'name': self.name, 'engine_obj': self.engine_obj}

    def __repr__(self):
        return f'Optics(name={self.name})'
