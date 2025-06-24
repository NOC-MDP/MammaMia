import json
from mamma_mia.exceptions import InvalidPlatform
from mamma_mia.sensors import create_sensor_class, SensorInventory
import os
from pathlib import Path
from loguru import logger
from attrs import frozen, field, define
from cattrs import structure, unstructure
import sys
from mamma_mia.log import log_filter
from enum import Enum
import numpy as np

sensor_inventory = SensorInventory()

class SensorBehavior(Enum):
    Upcast = ["climbing"]
    Downcast = ["diving"]
    Constant = ["climbing", "diving","hovering","surfaced"]

# Factory function to create a platform class
def create_platform_attrs(frozen_mode=False):
    base_decorator = frozen if frozen_mode else define

    # noinspection PyDataclass
    @base_decorator
    class PlatformAttrs:
        # platform parameters
        platform_type: str
        platform_manufacturer: str
        NEMA_coordinate_conversion: bool
        sensors: dict[str, create_sensor_class(frozen_mode=True)] = field(factory=dict)
        entity_name: str = None
        serial_number: str = None

        def register_sensor(self,sensor_type:str) -> None:
            """
            registers a sensor to a platform to use in a mission, checking it is a compatible sensor
            Args:
                sensor_type: instrument type
            """
            # TODO this is very dependant on strings exactly matching, ideally a more robust approach is needed.
            for sensor in sensor_inventory.entries.values():
                if sensor.instrument_type == sensor_type and self.platform_type in sensor.platform_compatibility:
                    sensor_unstruct = unstructure(sensor)
                    created_sensor = structure(sensor_unstruct, create_sensor_class(frozen_mode=False))
                    if self.entity_name is not None:
                        created_sensor.sensor_name = f"{self.entity_name}_{sensor.instrument_type}"
                    else:
                        created_sensor.sensor_name = f"{self.platform_type}_{self.platform_type}_{sensor.instrument_type}"
                    self.sensors[sensor_type] = created_sensor
                    logger.success(f"successfully created sensor {sensor_type} on entity {self.entity_name}")
                    return
            raise Exception(f"sensor type {sensor_type} not found for platform {self.platform_type}")


    return PlatformAttrs

@define
class Platform:
    attrs: create_platform_attrs()
    behaviour: np.ndarray = None

@frozen
class PlatformInventory:
    entries: dict[str,create_platform_attrs(frozen_mode=True)] = field(factory=dict)

    def __attrs_post_init__(self):
        # supress logs on import
        logger.remove()
        logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=log_filter)
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}platforms.json", "r") as f:
            plats = json.load(f)

        for platform_type, platforms2 in plats["platforms"].items():
            self._process_platform(platforms2)
        logger.log("COMPLETED","successfully created platform Inventory")

    def _process_platform(self, platforms2) -> None:
        """
        Processes the platform json entries that have been read into their appropriate sections of the catalog
        Args:
            platforms2:

        Returns:

        """
        for platform in platforms2:
            # TODO this is more complicated than just a Invalid platform exception need to handle it better
            try:
                platform_type = platform.get("platform_type")
                if not platform_type:
                    logger.error("Platform entry missing 'platform_type', skipping")
                    continue

                self.entries[platform_type] = structure(platform,create_platform_attrs(frozen_mode=True))
            except TypeError as e:
                logger.error(f"Error initializing platform: {e}")
                raise InvalidPlatform

    def create_entity(self,entity_name:str, platform: str,serial_number:str,NMEA_conversion:bool=None):
        """Returns a deep copy of a platform (prevents direct modification)."""
        if platform not in self.entries:
            raise KeyError(f"Platform '{platform}' not found in platform inventory.")
        platform_unstruct = unstructure(self.entries[platform])
        created_platform = structure(platform_unstruct,create_platform_attrs(frozen_mode=False))
        created_platform.entity_name = entity_name
        created_platform.serial_number = serial_number
        if NMEA_conversion is not None:
            created_platform.NEMA_coordinate_conversion = NMEA_conversion
        # register datalogger to platform
        created_platform.register_sensor(sensor_type="data_logger")
        logger.success(f"successfully created entity {created_platform.entity_name} of type {created_platform.platform_type}")
        return created_platform
