import json
from dataclasses import dataclass, field
from mamma_mia import sensors
from mamma_mia.exceptions import InvalidPlatform


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
    sensors: dict[str, sensors.Sensor]

    def __post_init__(self):
        # TODO add more validation and type checking here
        if not isinstance(self.bodc_platform_model_id, int):
            raise TypeError(f"bodc_platform_model_id must be an instance of int, got {type(self.bodc_platform_model_id)}")


    def register_sensor(self,sensor):
        if not isinstance(sensor, sensors.Sensor):  # Runtime type check
            raise TypeError(f"Sensor must be an instance of sensors.Sensor, got {type(sensor)}")
        self.sensors[sensor.sensor_name] = sensor

@dataclass
class PlatformCatalog:
    glider: dict = field(default_factory=dict)
    alr: dict = field(default_factory=dict)

    def __post_init__(self):

        with open("src/mamma_mia/platforms.json", "r") as f:
            plats = json.load(f)

        for platform_type, platforms in plats["platforms"].items():
            if platform_type == "glider":
                for platform in platforms:
                    try:
                        self.glider[platform["platform_name"]] = Platform(**platform)
                    except KeyError:
                        raise InvalidPlatform(f"{platform['platform_name']} is not a valid platform")

            if platform_type == "alr":
                for platform in platforms:
                    try:
                        self.alr[platform["platform_name"]] = Platform(**platform)
                    except KeyError:
                        raise InvalidPlatform(f"{platform['platform_name']} is not a valid platform")

platforms = PlatformCatalog()