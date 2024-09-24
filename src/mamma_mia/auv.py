from dataclasses import dataclass
from mamma_mia import sensors
from abc import ABC


@dataclass
class AUV(ABC):
    """
    Base class for glider objects
    """
    name: str
    sensors: sensors.SensorSuite


@dataclass
class Slocum(AUV):
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


@dataclass
class ALR1500(AUV):
    """
    Creates a ALR1500 object

    Parameters:
    - sensorsuite: SensorSuite object that comprises of one or more SensorGroups e.g. CTD, ADCP etc

    Returns:
    - ALR1500 object that can be used to fly through a world class
    """
    def __init__(self, sensorsuite: sensors.SensorSuite):
        self.name = "ALR1500"
        self.sensors = sensorsuite