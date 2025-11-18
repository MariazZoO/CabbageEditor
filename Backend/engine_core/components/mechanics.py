from typing import Any, Dict
from ..engine_import import load_corona_engine
from .geometry import Geometry

CoronaEngine = load_corona_engine()


class Mechanics:
    def __init__(self, geometry: Geometry, name: str = 'Mechanics'):
        if CoronaEngine is None:
            raise RuntimeError('CoronaEngine 未初始化')
        MechanicsCtor = getattr(CoronaEngine, 'Mechanics', None)
        if MechanicsCtor is None:
            raise RuntimeError('CoronaEngine 未提供 Mechanics 构造器')
        geo_obj = geometry.engine_obj if hasattr(geometry, 'engine_obj') else geometry
        self.engine_obj = MechanicsCtor(geo_obj)
        self.name = name
        self.geometry = geometry

    def to_dict(self) -> Dict[str, Any]:
        return {'name': self.name, 'engine_obj': self.engine_obj}

    def __repr__(self):
        return f'Mechanics(name={self.name})'
