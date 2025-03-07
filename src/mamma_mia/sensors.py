import json
from dataclasses import dataclass, field
from loguru import logger
from pathlib import Path
import os
import copy
from mamma_mia.parameters import Parameter, parameters
from mamma_mia.exceptions import InvalidParameter

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
        # convert all parameter strings to parameter objects
        for parameter_key in self.parameters.keys():
            self._process_parameters(parameter_key, parameters)

    def _process_parameters(self, parameter_key, parameters):
        parameter = None
        # TODO check that vars() is sensible here
        for k1 in vars(parameters).keys():
            for k2 in vars(parameters)[k1].keys():
                if k2 == parameter_key:
                    parameter = vars(parameters)[k1][k2]
        if parameter is None:
            raise InvalidParameter(f"parameter {parameter_key} not found")
        self.parameters[parameter_key] = parameter

    def register_parameter(self,parameter: Parameter):
        logger.info(f"registering parameter {parameter.parameter_name} to sensor {self.sensor_name}")
        # TODO add validation or checking here e.g. is it the right sensor type for the platform?
        if not isinstance(parameter, Parameter):  # Runtime type check
            raise TypeError(f"Sensor must be an instance of sensors.Sensor, got {type(parameter)}")
        self.parameters[parameter.parameter_name] = parameter
        logger.success(f"successfully registered parameter {parameter.parameter_name} to sensor {self.sensor_name}")


@dataclass
class SensorCatalog:
    _sensor_types = ("_CTD", "_radiometers", "_dataloggers")
    _CTD: dict = field(default_factory=dict, init=False)
    _radiometers: dict = field(default_factory=dict, init=False)
    _dataloggers: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        logger.info("Creating sensor catalog")
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}sensors.json", "r") as f:
            sens = json.load(f)

        for sensor_type, sensors in sens["sensors"].items():
            self._process_sensor(sensor_type, sensors)

    def _process_sensor(self, sensor_type, sensors):
        sensor_dict = self._get_sensor_dict(sensor_type)

        for sensor in sensors:
            sensor_ref = sensor.get("sensor_serial_number")
            if not sensor_ref:
                logger.error("Sensor entry missing 'sensor_serial_number', skipping")
                continue

            if sensor_ref in sensor_dict:
                logger.warning(f"Sensor '{sensor_ref}' already exists, skipping")
                continue

            try:
                sensor_dict[sensor_ref] = Sensor(**sensor)
            except TypeError as e:
                logger.error(f"Error initializing sensor {sensor_ref}: {e}")
                raise ValueError(f"{sensor_ref} is not a valid sensor")

    def get_sensor(self, sensor_type: str, sensor_ref: str):
        """Returns a deep copy of a sensor (prevents direct modification)."""
        sensor_dict = self._get_sensor_dict(sensor_type)
        if sensor_ref not in sensor_dict:
            raise KeyError(f"Sensor '{sensor_ref}' not found in {sensor_type}.")
        return copy.deepcopy(sensor_dict[sensor_ref])

    def add_sensor(self, sensor_type: str, sensor: Sensor):
        """Adds a new sensor. Raises an error if the sensor already exists."""
        sensor_dict = self._get_sensor_dict(sensor_type)
        sensor_name = sensor.sensor_name or sensor.sensor_serial_number
        if not sensor_name:
            raise ValueError("Sensor entry missing 'sensor_name' or 'sensor_serial_number'")
        if sensor_name in sensor_dict:
            raise ValueError(f"Sensor '{sensor_name}' already exists and cannot be modified.")

        sensor_dict[sensor_name] = sensor

    def remove_sensor(self, sensor_type: str, sensor_name: str):
        """Removes a sensor from the catalog."""
        sensor_dict = self._get_sensor_dict(sensor_type)
        if sensor_name not in sensor_dict:
            raise KeyError(f"Sensor '{sensor_name}' not found in {sensor_type}.")
        del sensor_dict[sensor_name]

    def list_sensors(self, sensor_type: str):
        """Lists all sensor names in the specified category (CTD, radiometers, dataloggers)."""
        return list(self._get_sensor_dict(sensor_type).keys())

    def _get_sensor_dict(self, sensor_type: str):
        """Helper function to get the correct sensor dictionary."""
        match sensor_type:
            case "CTD":
                return self._CTD
            case "radiometers":
                return self._radiometers
            case "dataloggers":
                return self._dataloggers
            case _:
                raise ValueError(
                    f"Invalid sensor type '{sensor_type}'. Must be 'CTD', 'radiometers', or 'dataloggers'.")

    def __setattr__(self, key, value):
        """Prevents direct modification of catalog attributes."""
        if key in self._sensor_types and hasattr(self, key):
            raise AttributeError(f"Cannot modify '{key}' directly. Use add_sensor or remove_sensor instead.")
        super().__setattr__(key, value)

    def __delattr__(self, key):
        """Prevents deletion of catalog attributes."""
        if key in self._sensor_types:
            raise AttributeError(f"Cannot delete '{key}'. Use remove_sensor instead.")
        super().__delattr__(key)


sensors = SensorCatalog()
