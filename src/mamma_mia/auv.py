from dataclasses import dataclass,field
from mamma_mia.sensors import CTD,BIO
import uuid
from loguru import logger

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
    sensor_arrays: dict = field(default_factory=dict)
    uuid: uuid = uuid.uuid4()

    def __post_init__(self):
        logger.success(f"{self.type.name} with id {self.id} created successfully")

    def add_sensor_arrays(self, sensor_array_list: list[CTD | BIO ]):
        # TODO add sensor array checks here
        i = 1
        for sensor_array in sensor_array_list:
            logger.info(f"adding sensor array {type(sensor_array).__name__} to {self.id}")
            self.sensor_arrays["sensor_array_"+str(i)] = sensor_array
            i = i + 1
        logger.success(f"{i-1} sensor arrays added to {self.id} successfully")