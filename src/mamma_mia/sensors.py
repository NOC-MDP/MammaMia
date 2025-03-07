import json
from dataclasses import dataclass, field
from mamma_mia.exceptions import InvalidSensor
from loguru import logger
from pathlib import Path
import os

@dataclass
class Sensor:
    # instance parameters
    sensor_serial_number: str
    bodc_sensor_version_id: int
    bodc_sensor_id: int
    sensor_name: str
    # type parameters
    bodc_sensor_model_id: int
    bodc_sensor_model_registry_id: int
    instrument_type: str
    sensor_manufacturer: str
    model_name: str
    sensor_model: str
    sample_rates: dict = field(default_factory=dict)
    parameters: dict = field(default_factory=dict)

    def __post_init__(self):
        # Ensure all values in the parameters dictionary are instances of Parameter
        for key, value in self.parameters.items():
            if not isinstance(value, int):  # Runtime type check
                raise TypeError(f"Parameter '{key}' must be an instance of parameters.Parameter, got {type(value)}")

        # TODO add more validation here

@dataclass
class SensorCatalog:
    CTD: dict[str, Sensor] = field(default_factory=dict)
    radiometers: dict[str, Sensor] = field(default_factory=dict)
    dataloggers: dict[str, Sensor] = field(default_factory=dict)

    def __post_init__(self):
        # Get the directory where the module is located
        module_dir = Path(__file__).parent
        # TODO need to not have a hardcoded path here
        with open(f"{module_dir}{os.sep}sensors.json", "r") as f:
            sens = json.load(f)
        for sensor_type, sensors in sens["sensors"].items():
            for sensor in sensors:
                # TODO check the InvalidSensor exception as this doens't look right?
                # TODO add more validation and checking here
                if sensor_type == "CTD":
                    try:
                        self.CTD[sensor["sensor_name"]] = Sensor(**sensor)
                    except KeyError:
                        raise InvalidSensor(f"{sensor['sensor_name']} is not a valid sensor")
                elif sensor_type == "radiometers":
                    try:
                        self.radiometers[sensor["sensor_name"]] = Sensor(**sensor)
                    except KeyError:
                        raise InvalidSensor(f"{sensor['sensor_name']} is not a valid sensor")
                elif sensor_type == "dataloggers":
                    try:
                        self.dataloggers[sensor["sensor_name"]] = Sensor(**sensor)
                    except KeyError:
                        raise InvalidSensor(f"{sensor['sensor_name']} is not a valid sensor")
                else:
                    logger.warning(f"unknown sensor type {sensor_type}")


sensors = SensorCatalog()
