from dataclasses import dataclass,field
import uuid
from loguru import logger

@dataclass(frozen=True)
class Slocum:
    """
    Slocum immutable type class
    """
    type: str = "slocum"
    description: str = "glider"

@dataclass(frozen=True)
class ALR1500:
    """
    ALR1500 immutable type class
    """
    type: str = "alr1500"
    description: str = "autosub long range 1500m"

@dataclass
class AUV:
    """
    Class to represent an autonomous underwater vehicle.

    Args:
        type: AUV type class
        id: AUV identification string e.g. ALR4

    Returns:
        populated AUV object with the relevant auv type class, identification string and system generated uuid.
    """
    type: Slocum | ALR1500
    id: str
    sensor_arrays: dict = field(default_factory=dict)
    uuid: uuid = uuid.uuid4()

    def __post_init__(self):
        logger.success(f"{self.type.type} with id {self.id} created successfully")

    def add_sensor_arrays(self, sensor_arrays):
        """
        Add sensor arrays to an auv object.
        Args:
            sensor_arrays: list of sensor arrays to add, e.g. CTD()

        Returns:
            void: sensor arrays are added to the auv object the method is run from

        """
        # TODO add sensor array checks here
        i = 1
        for sensor_array in sensor_arrays:
            logger.info(f"adding sensor array {type(sensor_array).__name__} to {self.id}")
            self.sensor_arrays["sensor_array_"+str(i)] = sensor_array
            i = i + 1
        logger.success(f"{i-1} sensor arrays added to {self.id} successfully")