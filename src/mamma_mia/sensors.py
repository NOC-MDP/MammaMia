from dataclasses import dataclass
from abc import ABC


class SensorSuite(dict):
    """
    Creates a sensorsuite object (extended python dict). This will only accept values that are SensorGroup instances

    Parameters:
    - None

    Returns:
    - empty sensorsuite dictionary
    """
    def __setitem__(self, key, value):
        """
        Inserts a sensorgroup object into the sensorsuite

        Parameters:
        - key: string to use to identifiy sensor group e.g. "CTD1"
        - value: sensorgroup instance

        Returns:
        - Updated sensorsuite dictionary
        """
        if not isinstance(value, SensorGroup):
            raise TypeError(f"Value must be an instance of SensorGroup, not {type(value).__name__}")
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value


@dataclass
class Sensor(ABC):
    """
    Abstract base class for all sensor types.
    """
    name: str
    units: str

@dataclass
class TemperatureSensor(Sensor):
    name: str = "temperature"
    units: str = "degrees C"

@dataclass
class SalinitySensor(Sensor):
    name: str = "salinity"
    units: str = "PSU"

@dataclass
class PressureSensor(Sensor):
    name: str = "pressure"
    units: str = "Pa"

@dataclass
class PhosphateSensor(Sensor):
    name: str = "phosphate"
    units: str = ""

@dataclass
class NitrateSensor(Sensor):
    name: str = "nitrate"
    units: str = ""

@dataclass
class SilicateSensor(Sensor):
    name: str = "silicate"
    units: str = ""

@dataclass
class SensorGroup(ABC):
    """
    Abstract base class for all sensor groups.
    """
    name: str
    sensors: dict[str, Sensor]


@dataclass
class CTD(SensorGroup):
    """
    creates a CTD sensor group, derived from SensorGroup.

    Parameters:
    - None

    Returns:
    - CTD sensor group (loaded with temperature, conductivity and pressure sensors)
    """
    def __init__(self):
        self.name = "CTD"
        # noinspection PyTypeChecker
        self.sensors = {
                        "temperature": TemperatureSensor,
                        "conductivity": SalinitySensor,
                        "pressure": PressureSensor,
                        }

@dataclass
class BIO(SensorGroup):
    """
    creates a CTD sensor group, derived from SensorGroup.

    Parameters:
    - None

    Returns:
    - CTD sensor group (loaded with temperature, conductivity and pressure sensors)
    """
    def __init__(self):
        self.name = "BIO"
        # noinspection PyTypeChecker
        self.sensors = {
                        "phosphate": PhosphateSensor,
                        "nitrate": NitrateSensor,
                        "silicate": SilicateSensor,
                        }

