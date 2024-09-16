from dataclasses import dataclass, field
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
class SensorGroup(ABC):
    """
    Abstract base class for all sensor groups.
    """
    name: str
    sensors: dict[str, Sensor] = field(default_factory=dict)


@dataclass
class CTD(SensorGroup):
    """
    creates a CTD sensor group, derived from SensorGroup.

    Parameters:
    - None

    Returns:
    - CTD sensor group (loaded with temperature, conductivity and pressure sensors)
    """
    name: str = "CTD"

    def __post_init__(self):
        self.sensors = {
                        "temperature": Sensor(name="temperature",units="degreesC"),
                        "conductivity": Sensor(name="salinity",units="PSU"),
                        "pressure": Sensor(name="pressure",units="Pa"),
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
    name: str = "CTD"

    def __post_init__(self):
        self.sensors = {
                        "phosphate": Sensor(name="phosphate",units=""),
                        "nitrate": Sensor(name="nitrate",units=""),
                        "silicate": Sensor(name="silicate",units=""),
                        }

