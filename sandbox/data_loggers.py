from dataclasses import dataclass, field
from mamma_mia.sensors import Sensor

@dataclass
class ALRDataLogger(Sensor):
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
class SlocumDataLogger(Sensor):
    bodc_sensor_model_id: int = field(default=450,init=False)
    bodc_sensor_model_registry_id: int = field(default=236,init=False)
    instrument_type: str = field(default="data loggers",init=False)
    sensor_manufacturer: str = field(default="Teledyne Webb Research",init=False)
    model_name: str = field(default="Slocum G1+G2 Glider Navigation data logger",init=False)
    sensor_model: str = field(default="Slocum G1+G2 Glider Navigation data logger",init=False)

    def __post_init__(self):
        pass

