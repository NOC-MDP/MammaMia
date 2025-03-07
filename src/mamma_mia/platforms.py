import json
from dataclasses import dataclass, field

from mamma_mia.exceptions import InvalidPlatform
from mamma_mia.sensors import sensors, Sensor
import os
from pathlib import Path
from loguru import logger
import copy

@dataclass
class Platform:
    # platform parameters
    bodc_platform_model_id: int
    platform_model_id: int
    nvs_platform_id: str
    platform_type: str
    platform_manufacturer: str
    platform_model_name: str
    # instance parameters
    bodc_platform_id: int
    bodc_platform_type_id: int
    platform_name: str
    platform_serial_number: str
    platform_owner: str
    platform_family: str
    wmo_platform_code: int
    data_type: str
    sensors: dict[str, Sensor] = field(default_factory=dict)

    def __post_init__(self):
        # TODO add more validation and type checking here
        if not isinstance(self.bodc_platform_model_id, int):
            raise TypeError(f"bodc_platform_model_id must be an instance of int, got {type(self.bodc_platform_model_id)}")

    def register_sensor(self,sensor):
        logger.info(f"registering sensor {sensor.sensor_name} to platform {self.platform_name}")
        # TODO add validation or checking here e.g. is it the right sensor type for the platform?
        if not isinstance(sensor, Sensor):  # Runtime type check
            raise TypeError(f"Sensor must be an instance of sensors.Sensor, got {type(sensor)}")
        self.sensors[sensor.sensor_name] = sensor
        logger.success(f"successfully registered sensor {sensor.sensor_name} to platform {self.platform_name}")

@dataclass
class PlatformCatalog:
    _glider: dict = field(default_factory=dict, init=False)
    _alr: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        logger.info("Creating platform catalog")
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}platforms.json", "r") as f:
            plats = json.load(f)

        for platform_type, platforms in plats["platforms"].items():
            self._process_platform(platform_type, platforms)
        logger.success("successfully create platform catalog")

    def _process_platform(self, platform_type, platforms):
        platform_dict = self._get_platform_dict(platform_type)

        for platform in platforms:
            # TODO look at this and see if a better error handling can be implemented
            try:
                platform_name = platform.get("platform_name")
                if not platform_name:
                    logger.error("Platform entry missing 'platform_name', skipping")
                    continue
                serial_number = platform.get("platform_serial_number")
                if not serial_number:
                    logger.error("Platform entry missing 'platform_serial_number', skipping")
                    continue
                datalogger = sensors.get_sensor(sensor_type="dataloggers",sensor_ref=serial_number)
                if not datalogger:
                    logger.error(f"Datalogger entry missing {serial_number}, skipping")

                platform_dict[platform_name] = Platform(**platform)
                platform_dict[platform_name].register_sensor(sensor=datalogger)

            except TypeError as e:
                logger.error(f"Error initializing platform {platform_name}: {e}")
                raise InvalidPlatform(f"{platform_name} is not a valid platform")

    def get_platform(self, platform_type: str, platform_name: str):
        """Returns a deep copy of a platform (prevents direct modification)."""
        platform_dict = self._get_platform_dict(platform_type)
        if platform_name not in platform_dict:
            raise KeyError(f"Platform '{platform_name}' not found in {platform_type}.")
        return copy.deepcopy(platform_dict[platform_name])

    def add_platform(self, platform_type: str, platform: Platform):
        """Adds a new platform. Raises an error if the platform already exists."""
        platform_dict = self._get_platform_dict(platform_type)
        platform_name = platform.platform_name
        if not platform_name:
            raise ValueError("Platform entry missing 'platform_name'")
        if platform_name in platform_dict:
            raise ValueError(f"Platform '{platform_name}' already exists and cannot be modified.")
        platform_dict[platform_name] = Platform(**platform)

    def remove_platform(self, platform_type: str, platform_name: str):
        """Removes a platform from the catalog."""
        platform_dict = self._get_platform_dict(platform_type)
        if platform_name not in platform_dict:
            raise KeyError(f"Platform '{platform_name}' not found in {platform_type}.")
        del platform_dict[platform_name]

    def list_platforms(self, platform_type: str):
        """Lists all platform names in the specified category (glider or alr)."""
        return list(self._get_platform_dict(platform_type).keys())

    def _get_platform_dict(self, platform_type: str):
        """Helper function to get the correct platform dictionary."""
        match platform_type:
            case "glider":
                return self._glider
            case "alr":
                return self._alr
            case _:
                raise ValueError(f"Invalid platform type '{platform_type}'. Must be 'glider' or 'alr'.")

    def __setattr__(self, key, value):
        """Prevents direct modification of catalog attributes."""
        if key in {"_glider", "_alr"} and hasattr(self, key):
            raise AttributeError(f"Cannot modify '{key}' directly. Use add_platform or remove_platform instead.")
        super().__setattr__(key, value)

    def __delattr__(self, key):
        """Prevents deletion of catalog attributes."""
        if key in {"_glider", "_alr"}:
            raise AttributeError(f"Cannot delete '{key}'. Use remove_platform instead.")
        super().__delattr__(key)


platforms = PlatformCatalog()