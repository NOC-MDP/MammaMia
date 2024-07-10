from dataclasses import dataclass
from src.mission import sensors
from abc import ABC


@dataclass
class AUV(ABC):
    name: str
    sensors: sensors.SensorSuite


@dataclass
class Slocum(AUV):
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "Slocum"
        self.sensors = sensorsuite


@dataclass
class Seaglider(AUV):
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "Seaglider"
        self.sensors = sensorsuite

