from dataclasses import dataclass
from src.mission import sensors
from abc import ABC


@dataclass
class Glider(ABC):
    """
    Base class for glider objects
    """
    name: str
    sensors: sensors.SensorSuite


@dataclass
class Slocum(Glider):
    """
    Creates a Slocum glider object

    Parameters:
    - sensorsuite: SensorSuite object that comprises of one or more SensorGroups e.g. CTD, ADCP etc

    Returns:
    - Glider object that can be used to fly through a world class
    """
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "Slocum"
        self.sensors = sensorsuite
