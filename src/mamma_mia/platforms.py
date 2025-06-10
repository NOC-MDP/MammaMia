import json
from mamma_mia.exceptions import InvalidPlatform, InvalidSensor
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
        nvs_platform_id: str
        platform_type: str
        platform_manufacturer: str
        platform_model_name: str
        # instance parameters
        platform_name: str
        platform_serial_number: str
        platform_owner: str
        platform_family: str
        wmo_platform_code: int
        data_type: str
        sensors: dict[str, create_sensor_class(frozen_mode=True)] = field(factory=dict)
        entity_name: str = None

        def list_compatible_sensors(self, sensor_type:str=None) -> dict:
            """
            Returns a list of sensors compatible with a given platform, results can be restricted to a specific sensor type e.g. CTD
            Args:

            Returns: list containing simplified sensor dicts (contains name and serial number)
            """
            sensors = {}
            for sensor in sensor_inventory.entries.values():
                if sensor_type is not None:
                    if sensor.instrument_type == sensor_type and self.platform_model_name in sensor.platform_compatibility:
                        if sensor.instrument_type not in sensors:
                            sensors[sensor.instrument_type] = [{"id":sensor.sensor_name, "serial_number":sensor.sensor_serial_number}]
                        else:
                            sensors[sensor.instrument_type].append({"id":sensor.sensor_name, "serial_number":sensor.sensor_serial_number})
                else:
                    if self.platform_serial_number in sensor.platform_compatibility:
                        if sensor.instrument_type not in sensors:
                            sensors[sensor.instrument_type] = [{"id":sensor.sensor_name, "serial_number":sensor.sensor_serial_number}]
                        else:
                            sensors[sensor.instrument_type].append({"id":sensor.sensor_name, "serial_number":sensor.sensor_serial_number})

            return sensors

        def register_sensor(self,sensor: create_sensor_class(frozen_mode=True)) -> None:
            """
            registers a sensor to a platform to use in a mission, checking it is a compatible sensor
            Args:
                sensor: Sensor class object
            """
            if self.platform_model_name not in sensor.platform_compatibility:
                logger.error(f"sensor {sensor.sensor_name} is not compatible with platform {self.platform_type}")
                raise InvalidSensor
            self.sensors[sensor.sensor_name] = sensor
            logger.success(f"successfully registered sensor {sensor.entity_name} to entity {self.entity_name}")


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
                platform_name = platform.get("platform_name")
                if not platform_name:
                    logger.error("Platform entry missing 'platform_name', skipping")
                    continue
                serial_number = platform.get("platform_serial_number")
                if not serial_number:
                    logger.error("Platform entry missing 'platform_serial_number', skipping")
                    continue
                datalogger = sensor_inventory.get_sensor(sensor_ref=serial_number)
                if datalogger.instrument_type != "data_loggers":
                    raise InvalidSensor(f"invalid instrument type {datalogger.instrument_type}")
                if not datalogger:
                    logger.error(f"Datalogger entry missing {serial_number}, skipping")

                self.entries[platform_name] = structure(platform,create_platform_attrs(frozen_mode=True))
                self.entries[platform_name].register_sensor(sensor=datalogger)

            except TypeError as e:
                logger.error(f"Error initializing platform: {e}")
                raise InvalidPlatform

    def create_entity(self,entity_name:str, platform: str):
        """Returns a deep copy of a platform (prevents direct modification)."""
        if platform not in self.entries:
            raise KeyError(f"Platform '{platform}' not found in platform inventory.")
        platform_unstruct = unstructure(self.entries[platform])
        created_platform = structure(platform_unstruct,create_platform_attrs(frozen_mode=False))
        created_platform.entity_name = entity_name
        logger.success(f"successfully created entity {created_platform.entity_name} as platform {platform} of type {created_platform.platform_type}")
        return created_platform

    def add_platform(self, platform: create_platform_attrs(frozen_mode=False)):
        """Adds a new platform. Raises an error if the platform already exists."""
        platform_name = platform.platform_name
        if not platform_name:
            raise ValueError("Platform entry missing 'platform_name'")
        if platform_name in self.entries:
            raise ValueError(f"Platform '{platform_name}' already exists and cannot be modified.")
        self.entries[platform_name] = platform

    def remove_platform(self, platform_name: str):
        """Removes a platform from the catalog."""

        if platform_name not in self.entries:
            raise KeyError(f"Platform '{platform_name}' not found in platform inventory.")
        del self.entries[platform_name]

