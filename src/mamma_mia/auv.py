from dataclasses import dataclass,field,InitVar
from mamma_mia.sensors import SensorSuite,CTD,BIO,ADCP
from abc import ABC
from loguru import logger

@dataclass
class AUV(ABC):
    """
    Base class for glider objects
    """
    type: str = field(init=False)
    id: str = field(init=False)
    sensor_suite: SensorSuite = field(init=False)

    def __post_init__(self):
        self.sensor_suite = SensorSuite()

    def add_sensor_arrays(self, sensor_array_list: list[CTD | BIO | ADCP ]):
        i = 1
        for sensor_array in sensor_array_list:
            logger.info(f"adding sensor array {i} to {self.id}")
            self.sensor_suite["sensor_"+str(i)] = sensor_array
            logger.info(f"added sensor {sensor_array.name} to {self.id}")
            i = i + 1
        logger.success(f"{i-1} sensor arrays added to {self.id} successfully")

@dataclass
class Slocum(AUV):
    """
    Creates a Slocum glider object

    Parameters:
    - sensorsuite: SensorSuite object that comprises one or more SensorGroups e.g. CTD, ADCP etc

    Returns:
    - Glider object that can be used to fly through a world-class
    """
    set_id: InitVar[str]

    def __post_init__(self, set_id):
        logger.info(f"creating auv of type Slocum with id {set_id}")
        self.sensor_suite = SensorSuite()
        self.id = set_id
        self.type = "Slocum"
        logger.success(f"Slocum with id {set_id} created successfully")


@dataclass
class ALR1500(AUV):
    """
    Creates a ALR1500 object

    Parameters:
    - sensorsuite: SensorSuite object that comprises one or more SensorGroups e.g. CTD, ADCP etc

    Returns:
    - ALR1500 object that can be used to fly through a world-class
    """
    set_id: InitVar[str]

    def __post_init__(self, set_id):
        logger.info(f"creating auv of type ALR1500 with ID: {set_id}")
        self.sensor_suite = SensorSuite()
        self.id = set_id
        self.type = "ALR1500"
        logger.success(f"ALR1500 with id {set_id} created successfully")
