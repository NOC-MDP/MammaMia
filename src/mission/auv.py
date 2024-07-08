from dataclasses import dataclass
from src.mission import sensors
from abc import ABC


@dataclass
class AUV(ABC):
    name: str
    dive_rate: float
    surface_rate: float
    speed: float
    max_depth: float
    sensors: sensors.SensorSuite


@dataclass
class Autosub(AUV):
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "Autosub"
        self.dive_rate = 1.0
        self.surface_rate = 1.0
        self.speed = 1.0
        self.max_depth = 1500.0
        self.sensors = sensorsuite


@dataclass
class Slocum(AUV):
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "Slocum"
        self.dive_rate = 2.0
        self.surface_rate = 2.0
        self.speed = 0.5
        self.max_depth = 200.0
        self.sensors = sensorsuite


AUVs = Autosub | Slocum
