import json
from attrs import define, field, frozen
from cattrs import structure,unstructure
from loguru import logger
from pathlib import Path
import os
import copy
import sys
from mamma_mia.parameters import Parameter, ParameterInventory
from mamma_mia.exceptions import InvalidParameter
from mamma_mia.log import log_filter

parameter_inventory = ParameterInventory()

def create_sensor_class(frozen_mode=False):
    base_decorator = frozen if frozen_mode else define

    # noinspection PyDataclass
    @base_decorator
    class Sensor:
        # instance parameters
        sensor_name: str
        # type parameters
        instrument_type: str
        parameters: dict = field(factory=dict)
        platform_compatibility: list = field(factory=list),
        entity_name: str = ""

        def __attrs_post_init__(self):
            # convert all parameter strings/keys to parameter objects
            for parameter_key in self.parameters:
                self._process_parameters(parameter_key,parameter_inventory)

        def _process_parameters(self, parameter_key, parameters2:ParameterInventory):
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

        def register_parameter(self, parameter: Parameter):
            # TODO add validation or checking here e.g. is it the right sensor type for the platform?
            if not isinstance(parameter, Parameter):  # Runtime type check
                raise TypeError(f"Parameter must be an instance of Parameter, or TimeParameter got {type(parameter)}")
            self.parameters[parameter.parameter_id] = parameter
            # TODO this log entry ends up being printed alot, it is probably useful sometimes but need to reduce its verbosity
            #logger.info(f"successfully registered parameter {parameter.parameter_name} to sensor {self.sensor_name}")

        if not frozen_mode:
            def __attrs_post_init__(self):
                # convert all parameter strings/keys to parameter objects
                for parameter_key in self.parameters:
                    self._process_parameters(parameter_key, parameter_inventory)

    return Sensor


@frozen
class SensorInventory:
    entries: dict[str,create_sensor_class(frozen_mode=True)] = field(factory=dict)

    def __attrs_post_init__(self):
        logger.remove()
        logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=log_filter)
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}sensors.json", "r") as f:
            sens = json.load(f)

        for sensor_type, sensors2 in sens["sensors"].items():
            self._process_sensor(sensors2)
        logger.log("COMPLETED","successfully created sensor inventory")

    def _process_sensor(self, sensors2):
        for sensor in sensors2:
            sensor_ref = sensor.get("sensor_name")
            if not sensor_ref:
                logger.error("Sensor entry missing 'sensor_name', skipping")
                continue

            if sensor_ref in self.entries:
                logger.warning(f"Sensor '{sensor_ref}' already exists, skipping")
                continue

            try:
                self.entries[sensor_ref] = structure(sensor,create_sensor_class(frozen_mode=True))
            except TypeError as e:
                logger.error(f"Error initializing sensor {sensor_ref}: {e}")
                raise ValueError(f"{sensor_ref} is not a valid sensor")

    def list_sensors(self):
        """Lists all sensor names"""
        return list(self.entries.keys())

