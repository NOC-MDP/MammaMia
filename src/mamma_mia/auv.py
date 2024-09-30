from dataclasses import dataclass,field,asdict
from loguru import logger
import uuid

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

    def to_dict(self):
        return {k: v.to_dict() for k, v in self.items()}


@dataclass
class Sensor:
    """
    class for all sensor types.
    """
    type: str
    units: str


@dataclass
class SensorArray:
    """
    Abstract base class for all sensor groups.
    """
    name: str
    uuid: str
    sensors: dict[str, Sensor]

    def to_dict(self):
        return {k: str(v) for k, v in asdict(self).items()}


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
        super().__init__(name="CTD",
                         sensors= {
                            "sensor_1": Sensor(type="temperature",units="degreesC"),
                            "sensor_2": Sensor(type="salinity",units="PSU"),
                            "sensor_3": Sensor(type="pressure",units="bar"),
                        },
                        uuid=str(uuid.uuid4()))


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
        super().__init__(name="BIO",
                         sensors= {
                            "sensor_1": Sensor(type="phosphate",units="mmol kg-3"),
                            "sensor_2": Sensor(type="nitrate",units="mmol kg-3"),
                            "sensor_3": Sensor(type="silicate",units="mmol kg-3"),
                        },
                         uuid=str(uuid.uuid4()))

@dataclass
class ADCP(SensorArray):
    """
    creates a CTD sensor group, derived from SensorGroup.

    Parameters:
    - None

    Returns:
    - CTD sensor group (loaded with temperature, conductivity and pressure sensors)
    """
    def __init__(self):
        super().__init__(name="ADCP",
                         sensors = {
                            "sensor_1": Sensor(type="u_component",units="ms-1"),
                            "sensor_2": Sensor(type="v_component",units="ms-1"),
                            "sensor_3": Sensor(type="w_component",units="ms-1"),
                         },
                        uuid=str(uuid.uuid4()))

# classes with different AUV parameters derived from type
@dataclass(frozen=True)
class Slocum:
    name: str = "Slocum"

@dataclass(frozen=True)
class ALR1500:
    name: str = "ALR1500"

@dataclass
class AUV:
    """
    Base class for glider objects

    """
    type: Slocum | ALR1500
    id: str
    sensor_suite: SensorSuite = field(default_factory=SensorSuite)
    uuid: uuid = uuid.uuid4()

    def __post_init__(self):
        logger.success(f"{self.type.name} with id {self.id} created successfully")

    def add_sensor_arrays(self, sensor_array_list: list[CTD | BIO | ADCP ]):
        i = 1
        for sensor_array in sensor_array_list:
            logger.info(f"adding sensor array {type(sensor_array).__name__} to {self.id}")
            self.sensor_suite["sensor_array_"+str(i)] = sensor_array
            i = i + 1
        logger.success(f"{i-1} sensor arrays added to {self.id} successfully")