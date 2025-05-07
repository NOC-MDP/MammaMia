import json
from pathlib import Path
import os
from loguru import logger
import copy
from attrs import frozen, field
from cattrs import structure
import sys
from mamma_mia.log import log_filter

@frozen
class Parameter:
    parameter_id: str
    identifier: str
    vocab_url: str
    standard_name: str
    unit_of_measure: str
    unit_identifier: str
    parameter_definition: str
    alternate_labels: list[str]
    source_names: list[str]


@frozen
class ParameterInventory:
    entries: dict[str,Parameter] = field(factory=dict)

    def __attrs_post_init__(self):
        logger.remove()
        logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=log_filter)
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}parameters.json", "r") as f:
            params = json.load(f)

        for parameter_type, parameters2 in params["parameters"].items():
            self._process_parameters(parameter_type, parameters2)

        logger.log("COMPLETED","Successfully created parameter inventory")

    def _process_parameters(self, parameter_type, parameters2):
        for parameter in parameters2:
            try:
                self.entries[parameter["parameter_id"]] = structure(parameter,Parameter)
            except TypeError as e:
                logger.error(e)
                raise ValueError(f"{parameter['parameter_id']} is not a valid {parameter_type} parameter")
            logger.info(f"parameter {parameter['parameter_id']} registered successfully")

    def get_parameter(self,parameter_id: str):
        """Returns a copy of the requested parameter to prevent modification."""
        if parameter_id in self.entries:
            return copy.deepcopy(self.entries[parameter_id])
        raise KeyError(f"Parameter '{parameter_id}' not found in parameter inventory")

    def add_parameter(self,parameter: Parameter):
        """Adds a new parameter, preventing modifications to existing ones."""
        if parameter.parameter_id in self.entries:
            raise AttributeError(f"Parameter '{parameter.parameter_id}' already exists and cannot be modified.")
        self.entries[parameter.parameter_id] = parameter

    def remove_parameter(self,parameter_name: str):
        """Removes a parameter from the catalog."""
        if parameter_name in self.entries:
            del self.entries[parameter_name]
        else:
            raise KeyError(f"Parameter '{parameter_name}' not found in parameter inventory")

