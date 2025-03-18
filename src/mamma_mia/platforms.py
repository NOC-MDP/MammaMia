import json
from mamma_mia.exceptions import InvalidPlatform, InvalidSensor, InvalidSensorBehaviour
from mamma_mia.sensors import sensor_inventory, create_sensor_class, SensorBehaviour, SensorMode
import os
from pathlib import Path
from loguru import logger
from attrs import frozen, field, define
from cattrs import structure, unstructure
import sys
from mamma_mia.log import log_filter



# Factory function to create a platform class
def create_platform_class(frozen_mode=False):
    base_decorator = frozen if frozen_mode else define

    # noinspection PyDataclass
    @base_decorator
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
        # TODO make the two enums below actually do something
        science_sensor_behaviour: SensorBehaviour = SensorBehaviour.ALL_ON_FAST_AS_POSSIBLE
        science_sensor_mode: SensorMode = SensorMode.DECOUPLED
        sensors: dict[str, create_sensor_class(frozen_mode=True)] = field(factory=dict)
        entity_name: str = None

        def list_compatible_sensors(self, sensor_type:str=None) -> list[create_sensor_class(frozen_mode=True)]:
            """
            Returns a list of sensors compatible with a given platform, results can be restricted to a specific sensor type e.g. CTD
            Args:
                sensor_type: string denoting the sensor type, if not specified, all compatible sensors are returned

            Returns: list containing Sensor class objects

            """
            return sensor_inventory.list_compatible_sensors(sensor_type=sensor_type, platform_type=self.platform_type)

        def register_sensor(self,sensor: create_sensor_class(frozen_mode=True)) -> None:
            """
            registers a sensor to a platform to use in a mission, checking it is a compatible sensor
            Args:
                sensor: Sensor class object
            """
            if self.platform_type not in sensor.platform_compatibility:
                logger.error(f"sensor {sensor.sensor_name} is not compatible with platform {self.platform_type}")
                raise InvalidSensor
            self.sensors[sensor.sensor_name] = sensor
            logger.success(f"successfully registered sensor {sensor.sensor_name} to entity {self.entity_name}")

        if not frozen_mode:
            def update_sensor_behaviour(self, sensor_behaviour: str) -> None:
                """
                Update the sensor behaviour from default all on as fast as possible (sample at max rate)
                Args:
                    sensor_behaviour:

                Returns:

                """
                logger.critical(f"sensor behaviour {sensor_behaviour} is not implemented yet")
                match sensor_behaviour:
                    case "all_on_fast_as_possible":
                        behaviour = SensorBehaviour.ALL_ON_FAST_AS_POSSIBLE
                    case "60_seconds_upcast":
                        behaviour = SensorBehaviour.SIXTY_SECONDS_UPCAST
                    case _:
                        logger.error(f"sensor behaviour {sensor_behaviour} is invalid")
                        raise InvalidSensorBehaviour
                self.science_sensor_behaviour = behaviour
                #logger.success(f"successfully updated sensor behaviour for entity {self.entity_name} to {behaviour.value}")

            def toggle_sensor_coupling(self) -> None:
                """
                toggle sensor coupling so each sensor will sample at its defined rate
                Returns:

                """
                logger.critical("sensor coupling is not yet implemented")
                if self.science_sensor_mode == SensorMode.COUPLED:
                    self.science_sensor_mode = SensorMode.DECOUPLED
                    #logger.success(f"scientific sensors on entity {self.entity_name} are now decoupled")
                elif self.science_sensor_mode == SensorMode.DECOUPLED:
                    self.science_sensor_mode = SensorMode.COUPLED
                    #logger.success(f"scientific sensors on entity {self.entity_name} are now coupled")
                else:
                    logger.warning(f"sensor mode {self.science_sensor_mode} is not supported")

    return Platform

@frozen
class PlatformInventory:
    _glider: dict = field(factory=dict)
    _alr: dict = field(factory=dict)

    def __attrs_post_init__(self):
        # supress logs on import
        logger.remove()
        logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=log_filter)
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}platforms.json", "r") as f:
            plats = json.load(f)

        for platform_type, platforms2 in plats["platforms"].items():
            self._process_platform(platform_type, platforms2)
        logger.log("COMPLETED","successfully created platform Inventory")

    def _process_platform(self, platform_type, platforms2) -> None:
        """
        Processes the platform json entries that have been read into their appropriate sections of the catalog
        Args:
            platform_type:
            platforms2:

        Returns:

        """
        platform_dict = self._get_platform_dict(platform_type)
        for platform in platforms2:
            # TODO look at this is .get the best thing to use? maybe try except key error?
            try:
                platform_name = platform.get("platform_name")
                if not platform_name:
                    logger.error("Platform entry missing 'platform_name', skipping")
                    continue
                serial_number = platform.get("platform_serial_number")
                if not serial_number:
                    logger.error("Platform entry missing 'platform_serial_number', skipping")
                    continue
                datalogger = sensor_inventory.get_sensor(sensor_type="dataloggers",sensor_ref=serial_number)
                if not datalogger:
                    logger.error(f"Datalogger entry missing {serial_number}, skipping")

                platform_dict[platform_name] = structure(platform,create_platform_class(frozen_mode=True))
                platform_dict[platform_name].register_sensor(sensor=datalogger)

            except TypeError as e:
                logger.error(f"Error initializing platform: {e}")
                raise InvalidPlatform

    def create_entity(self,entity_name:str, platform_type: str, platform: str):
        """Returns a deep copy of a platform (prevents direct modification)."""
        platform_dict = self._get_platform_dict(platform_type)
        if platform not in platform_dict:
            raise KeyError(f"Platform '{platform}' not found in {platform_type}.")
        platform_unstruct = unstructure(platform_dict[platform])
        created_platform = structure(platform_unstruct,create_platform_class(frozen_mode=False))
        created_platform.entity_name = entity_name
        logger.success(f"successfully created entity {entity_name} as platform {platform} of type {platform_type}")
        return created_platform

    def add_platform(self, platform_type: str, platform: create_platform_class(frozen_mode=False)):
        """Adds a new platform. Raises an error if the platform already exists."""
        platform_dict = self._get_platform_dict(platform_type)
        platform_name = platform.platform_name
        if not platform_name:
            raise ValueError("Platform entry missing 'platform_name'")
        if platform_name in platform_dict:
            raise ValueError(f"Platform '{platform_name}' already exists and cannot be modified.")
        platform_dict[platform_name] = platform

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
    
    @staticmethod
    def list_platform_types():
        """
        Lists all available platform types.
        Returns: list of platform types.

        """
        return ["alr", "glider"]

platform_inventory = PlatformInventory()