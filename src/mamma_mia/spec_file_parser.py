from dataclasses import dataclass, field
from typing import List
import cattrs

@dataclass
class GliderSim
    lat_ini: List[float]
    lon_ini: List[float]
    dive_depth: float
    lat_wp: List[float]
    lon_wp: List[float]
    initial_heading: float
    glider_model: str
    dt: float
    CPUcycle: int
    maxSimulationTime: int
    end_on_surfacing: bool
    end_on_grounding: bool
    verbose:bool
    glider_gps_acquiretime: float
    mission_initialisation_time: int
s
@dataclass
class FlightModel
    Cd0: float
    mg: float
    Vg: float
    T1: int
    T2: float
    T3: float

@dataclass
class GliderSimBathymetry
    elevation_name: str
    elevation_factor: int
    lat_name: str
    lon_name: str
    file_path: str

@dataclass
class GeospatialExtent
    lat_max: float
    lat_min: float
    lon_max: float
    lon_min: float
    time_coverage_start: str
    time_coverage_end: str

@dataclass
class SensorSpecification
    source_id: str
    variable_name: str
    accuracy: float
    resolution: float
    drift_per_month: float
    range: List[float]
    percent_errors: bool
    noise_std: float
