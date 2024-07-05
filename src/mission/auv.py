from dataclasses import dataclass
from src.mission import sensors

@dataclass
class AUV:
    name: str
    dive_rate: float
    surface_rate: float
    speed: float
    max_depth: float
    sensors: sensors.Sensors


@dataclass
class Autosub(AUV):
    def __init__(self,sensors:sensors.Sensors):
        self.name = "Autosub"
        self.dive_rate = 1.0
        self.surface_rate = 1.0
        self.speed = 1.0
        self.max_depth = 1500.0
        self.sensors = sensors

@dataclass
class Slocum(AUV):
    def __init__(self,sensors:sensors.Sensors):
        self.name = "Slocum"
        self.dive_rate = 2.0
        self.surface_rate = 2.0
        self.speed = 0.5
        self.max_depth = 200.0
        self.sensors = sensors

AUVs = Autosub | Slocum

