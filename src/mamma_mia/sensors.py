import json
from dataclasses import dataclass, field
from mamma_mia.exceptions import InvalidSensor

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
    sensors: dict[str, Sensor] = field(default_factory=dict)

    def __post_init__(self):
        with open("src/mamma_mia/sensors.json", "r") as f:
            sens = json.load(f)
        for sensor_type, sensors in sens["sensors"].items():
            for sensor in sensors:
                try:
                    self.sensors[sensor["sensor_name"]] = Sensor(**sensor)
                except KeyError:
                    raise InvalidSensor(f"{sensor['sensor_name']} is not a valid sensor")

sensors = SensorCatalog()
