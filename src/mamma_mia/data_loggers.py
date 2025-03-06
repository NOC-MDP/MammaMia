from dataclasses import dataclass, field
from mamma_mia.sensors import Sensor2

@dataclass
class ALRDataLogger(Sensor2):
    bodc_sensor_model_id: int = field(default=761,init=False)
    bodc_sensor_model_registry_id: int = field(default=281,init=False)
    instrument_type: str = field(default="data loggers",init=False)
    sensor_manufacturer: str = field(default="National Oceanography Centre",init=False)
    model_name: str = field(default="Autosub Long Range v2 {ALR} data logger",init=False)
    sensor_model: str = field(default="Autosub Long Range v2 {ALR} data logger",init=False)

    def __post_init__(self):
        pass
        #self.parameters = {"Latitude":ALR_Latitude}

@dataclass
class SlocumDataLogger(Sensor2):
    bodc_sensor_model_id: int = field(default=450,init=False)
    bodc_sensor_model_registry_id: int = field(default=236,init=False)
    instrument_type: str = field(default="data loggers",init=False)
    sensor_manufacturer: str = field(default="Teledyne Webb Research",init=False)
    model_name: str = field(default="Slocum G1+G2 Glider Navigation data logger",init=False)
    sensor_model: str = field(default="Slocum G1+G2 Glider Navigation data logger",init=False)

    def __post_init__(self):
        pass

Teledyne_Slocum_G1_G2_unit_398 = SlocumDataLogger(
    bodc_sensor_version_id=1139,
    bodc_sensor_id=686,
    sensor_name="Teledyne Slocum G1+G2 unit_398",
    sensor_serial_number="unit_398"
)

ALR_v1_data_logger_ALR_4 = ALRDataLogger(
    bodc_sensor_version_id=1296,
    bodc_sensor_id=838,
    sensor_name="ALR v1 data logger ALR_4",
    sensor_serial_number="ALR_4",
)

ALR_v2_data_logger_ALR_6 = ALRDataLogger(
    bodc_sensor_version_id=1664,
    bodc_sensor_id=1232,
    sensor_name="ALR data logger v2 ALR_6",
    sensor_serial_number="ALR_6"
)