import json
from attrs import frozen, field
from cattrs import structure
from loguru import logger
from pathlib import Path
import os
import copy
import sys

from mamma_mia.parameters import Parameter, parameters,TimeParameter
from mamma_mia.exceptions import InvalidParameter
from mamma_mia.log import import_log_filter

@frozen
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
    parameters: dict = field(factory=dict),
    platform_compatibility: list = field(factory=list),

    def __attrs_post_init__(self):
        # convert all parameter strings/keys to parameter objects
        for parameter_key in self.parameters.keys():
            self._process_parameters(parameter_key, parameters)


    def _process_parameters(self, parameter_key, parameters2):
        parameter = None
        for k1 in parameters2.__attrs_attrs__:  # Iterate over attrs fields
            sub_obj = getattr(parameters2, k1.name)  # Get the field's value
            if isinstance(sub_obj, dict):
                for k2 in sub_obj.keys():
                    if k2 == parameter_key:
                        parameter = sub_obj[k2]
        if parameter is None:
            raise InvalidParameter(f"parameter {parameter_key} not found")
        self.register_parameter(parameter=parameter)

    def register_parameter(self,parameter: Parameter):
        # TODO add validation or checking here e.g. is it the right sensor type for the platform?
        if not isinstance(parameter, (Parameter,TimeParameter)):  # Runtime type check
            raise TypeError(f"Parameter must be an instance of Parameter, or TimeParameter got {type(parameter)}")
        self.parameters[parameter.parameter_name] = parameter
        logger.info(f"successfully registered parameter {parameter.parameter_name} to sensor {self.sensor_name}")


@frozen
class SensorCatalog:
    _CTD: dict = field(factory=dict)
    _radiometers: dict = field(factory=dict)
    _dataloggers: dict = field(factory=dict)

    def __attrs_post_init__(self):
        logger.remove()
        logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=import_log_filter)
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}sensors.json", "r") as f:
            sens = json.load(f)

        for sensor_type, sensors2 in sens["sensors"].items():
            self._process_sensor(sensor_type, sensors2)
        logger.success("successfully created sensor catalog")

    def _process_sensor(self, sensor_type, sensors2):
        sensor_dict = self._get_sensor_dict(sensor_type)

        for sensor in sensors2:
            sensor_ref = sensor.get("sensor_serial_number")
            if not sensor_ref:
                logger.error("Sensor entry missing 'sensor_serial_number', skipping")
                continue

            if sensor_ref in sensor_dict:
                logger.warning(f"Sensor '{sensor_ref}' already exists, skipping")
                continue

            try:
                sensor_dict[sensor_ref] = structure(sensor,Sensor)
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
        return list(self._get_sensor_dict(sensor_type).values())

    @staticmethod
    def list_sensor_types():
        """
        Lists all available sensor types.
        Returns: list of sensor types.

        """
        return ["CTD", "radiometers", "dataloggers"]

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

    def list_compatible_sensors(self, platform_type: str, sensor_type: str = None):
        """
        Returns a list of compatible sensors for a given platform type
        Args:
            platform_type: string denoting the platform type
            sensor_type: string denoting the sensor type, if not specified, all compatible sensors are returned

        Returns:

        """
        sensors_compatible = []
        if sensor_type is None:
            sensor_types = self.list_sensor_types()
        else:
            sensor_types = [sensor_type]
        for sensor_type in sensor_types:
            sensors2 = self._get_sensor_dict(sensor_type)
            for key, sensor in sensors2.items():
                if platform_type in sensor.platform_compatibility:
                    sensors_compatible.append(sensor)
        return sensors_compatible


sensors = SensorCatalog()
