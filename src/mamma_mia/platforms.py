from dataclasses import dataclass, field
from mamma_mia import sensors
from mamma_mia import data_loggers

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
    sensors: dict = field(default_factory=dict)

    def __post_init__(self):
        # Ensure all values in the sensors dictionary are instances of Sensor
        for key, value in self.sensors.items():
            if not isinstance(value, sensors.Sensor2):  # Runtime type check
                raise TypeError(f"Sensor '{key}' must be an instance of sensors.Sensor, got {type(value)}")

    def add_sensor(self,key:str,sensor):
        if not isinstance(sensor, sensors.Sensor2):  # Runtime type check
            raise TypeError(f"Sensor '{key}' must be an instance of sensors.Sensor, got {type(sensor)}")
        self.sensors[key] = sensor


@dataclass
class SlocumPlatform(Platform):
    bodc_platform_model_id: int = field(default=117, init=False)
    platform_model_id: int = field(default=358, init=False)
    nvs_platform_id: str = field(default="B7600001", init=False)
    platform_type: str = field(default="slocum", init=False)
    platform_manufacturer: str = field(default="Teledyne Webb Research", init=False)
    platform_model_name: str = field(default="G2", init=False)


@dataclass
class ALRPlatform(Platform):
    bodc_platform_model_id: int = field(default=274, init=False)
    platform_model_id: int = field(default=682, init=False)
    nvs_platform_id: str = field(default="B7600021", init=False)
    platform_type: str = field(default="Autosub Long Range", init=False)
    platform_manufacturer: str = field(default="National Oceanography Centre", init=False)
    platform_model_name: str = field(default="Autosub Long Range 1500", init=False)


Churchill = SlocumPlatform(
    bodc_platform_id=862,
    bodc_platform_type_id=402,
    platform_name="Churchill",
    platform_serial_number="unit_398",
    platform_owner="NOCS",
    platform_family="open ocean glider",
    wmo_platform_code=6801573,
    data_type="EGO glider time-series data",
    sensors={"data_logger": data_loggers.Teledyne_Slocum_G1_G2_unit_398}
)


ALR4 = ALRPlatform(
    bodc_platform_id=1295,
    bodc_platform_type_id=837,
    platform_name="ALR_4",
    platform_serial_number="ALR_4",
    platform_owner="NOCS",
    platform_family="open ocean glider",
    wmo_platform_code=-9999999,
    data_type="EGO glider time-series data",
    sensors={"data_logger":data_loggers.ALR_v1_data_logger_ALR_4}
)

def availble():
    AUVs = {"gliders": ["Churchill"],"ALRs": ["ALR_4"]}
    return AUVs
