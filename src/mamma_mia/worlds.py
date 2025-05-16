import numpy as np
from attrs import frozen, define

@frozen
class WorldExtent:
    lat_max: np.float64
    lat_min: np.float64
    lon_max: np.float64
    lon_min: np.float64
    time_start: str
    time_end: str
    depth_max: np.float64

@define
class WorldsAttributes:
    extent: WorldExtent
    catalog_priorities: dict
    interpolator_priorities: dict
    matched_worlds: dict

@define
class WorldsConf:
    attributes: WorldsAttributes
    worlds: dict
    stores: dict