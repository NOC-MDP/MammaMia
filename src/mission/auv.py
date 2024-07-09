from dataclasses import dataclass
from src.mission import sensors
from abc import ABC


@dataclass
class AUV(ABC):
    name: str
    dive_rate: float
    dive_angle: float
    surface_rate: float
    surface_angle: float
    time_at_surface: int  #time step intervals
    time_at_depth: int  # time_step intervals
    time_step: int  # seconds
    speed: float
    target_depth: float
    min_depth: float
    sensors: sensors.SensorSuite


@dataclass
class Slocum(AUV):
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "Slocum"
        self.dive_rate = 0.24
        self.dive_angle = 27.0
        self.surface_rate = 0.19
        self.surface_angle = 27.0
        self.speed = 0.25
        self.time_at_surface = 10
        self.time_at_depth = 10
        self.time_step = 60
        self.target_depth = 200.0
        self.min_depth = 0.5
        self.sensors = sensorsuite


@dataclass
class Autosub(AUV):
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "Autosub"
        self.dive_rate = 0.24
        self.dive_angle = 27.0
        self.surface_rate = 0.19
        self.surface_angle = 27.0
        self.speed = 0.25
        self.time_at_surface = 10
        self.time_at_depth = 10
        self.time_step = 60
        self.target_depth = 200.0
        self.min_depth = 0.5
        self.sensors = sensorsuite

