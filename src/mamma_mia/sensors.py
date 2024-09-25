from dataclasses import dataclass
from abc import ABC


class SensorSuite(dict):
    """
    Creates a sensorsuite object (extended python dict). This will only accept values that are SensorArray instances

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
        if not isinstance(value, SensorArray):
            raise TypeError(f"Value must be an instance of SensorArray, not {type(value).__name__}")
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

@dataclass
class Sensor:
    """
    class for all sensor types.
    """
    type: str
    units: str


@dataclass
class SensorArray(ABC):
    """
    Abstract base class for all sensor groups.
    """
    name: str
    sensors: dict[str, Sensor]


@dataclass
class CTD(SensorArray):
    """
    creates a CTD sensor group, derived from SensorGroup.

    Parameters:
    - None

    Returns:
    - CTD sensor group (loaded with temperature, conductivity and pressure sensors)
    """
    def __init__(self):
        self.name = "CTD"
        self.sensors = {
                        "sensor_1": Sensor(type="temperature",units="degreesC"),
                        "sensor_2": Sensor(type="salinity",units="PSU"),
                        "sensor_3": Sensor(type="pressure",units="bar"),
                        }

@dataclass
class BIO(SensorArray):
    """
    creates a CTD sensor group, derived from SensorGroup.

    Parameters:
    - None

    Returns:
    - CTD sensor group (loaded with temperature, conductivity and pressure sensors)
    """
    def __init__(self):
        self.name = "BIO"
        self.sensors = {
                        "sensor_1": Sensor(type="phosphate",units="mmol kg-3"),
                        "sensor_2": Sensor(type="nitrate",units="mmol kg-3"),
                        "sensor_3": Sensor(type="silicate",units="mmol kg-3"),
                        }

@dataclass
class ADCP(SensorArray):
    """
    creates a CTD sensor group, derived from SensorGroup.

    Parameters:
    - None

    Returns:
    - CTD sensor group (loaded with temperature, conductivity and pressure sensors)
    """
    # TODO need to figure out how to handle multiple channels
    def __init__(self):
        self.name = "ADCP"
        self.sensors = {
                        "sensor_1": Sensor(type="u_component",units="ms-1"),
                        "sensor_2": Sensor(type="v_component",units="ms-1"),
                        "sensor_3": Sensor(type="w_component",units="ms-1"),
                        }
