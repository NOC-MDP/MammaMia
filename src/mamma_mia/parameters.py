import json
from pathlib import Path
import os
from loguru import logger
import copy
from attrs import frozen, field
from cattrs import structure

@frozen
class TimeParameter:
    parameter_name: str
    long_name: str
    units: str
    standard_name: str
    valid_min: float
    valid_max: float
    calendar: str
    fill_value: float


@frozen
class Parameter:
    parameter_name: str
    standard_name: str
    unit_of_measure: str
    parameter_definition: str
    seadatanet_parameter: str
    seadatanet_unit_of_measure: str
    source_name: str
    ancillary_variables: str
    fill_value: float = 99999.0
    valid_max: float = None
    valid_min: float = None


@frozen
class ParameterCatalog:
    _environmental: dict[str, Parameter] = field(factory=dict)
    _navigation: dict[str, Parameter] = field(factory=dict)
    _time: dict[str, TimeParameter] = field(factory=dict)

    def __attrs_post_init__(self):
        logger.info("Creating parameter catalog")
        module_dir = Path(__file__).parent
        with open(f"{module_dir}{os.sep}parameters.json", "r") as f:
            params = json.load(f)

        for parameter_type, parameters in params["parameters"].items():
            self._process_parameters(parameter_type, parameters)

        logger.info("Successfully created parameter catalog")

    def _process_parameters(self, parameter_type, parameters):
        param_dict = self._get_parameter_dict(parameter_type)

        for parameter in parameters:
            try:
                logger.info(f"registering parameter {parameter['parameter_name']} to catalog")
                param_dict[parameter["parameter_name"]] = (
                    structure(parameter,TimeParameter) if parameter_type == "time" else structure(parameter,Parameter)
                )
            except TypeError as e:
                logger.error(e)
                raise ValueError(f"{parameter['parameter_name']} is not a valid {parameter_type} parameter")
            logger.success(f"paramter {parameter['parameter_name']} registered successfully")

    def _get_parameter_dict(self, parameter_type):
        match parameter_type:
            case "environmental":
                return self._environmental
            case "navigation":
                return self._navigation
            case "time":
                return self._time
            case _:
                raise ValueError(f"Unknown parameter type {parameter_type}")

    def get_parameter(self, parameter_type: str, parameter_name: str):
        """Returns a copy of the requested parameter to prevent modification."""
        param_dict = self._get_parameter_dict(parameter_type)
        if parameter_name in param_dict:
            return copy.deepcopy(param_dict[parameter_name])
        raise KeyError(f"Parameter '{parameter_name}' not found in '{parameter_type}'")

    def add_parameter(self, parameter_type: str, parameter: Parameter):
        """Adds a new parameter, preventing modifications to existing ones."""
        param_dict = self._get_parameter_dict(parameter_type)
        if parameter.parameter_name in param_dict:
            raise AttributeError(f"Parameter '{parameter.parameter_name}' already exists and cannot be modified.")
        param_dict[parameter.parameter_name] = parameter

    def remove_parameter(self, parameter_type: str, parameter_name: str):
        """Removes a parameter from the catalog."""
        param_dict = self._get_parameter_dict(parameter_type)
        if parameter_name in param_dict:
            del param_dict[parameter_name]
        else:
            raise KeyError(f"Parameter '{parameter_name}' not found in '{parameter_type}'")


parameters = ParameterCatalog()




# TEMP_DOXY = Parameter(
#     parameter_name = "TEMP_DOXY",
#       unit_of_measure = "degree_Celsius",
#       parameter_definition="Temperature of oxygen determination by optode",
#       seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/OXYTAAOP/",
#       seadatanet_unit_of_measure="SDN:P06::UPAA",
#       source_name="sci_oxy4_temp"
# )
#

# WATERCURRENTS_U = Parameter(
#     parameter_name = "WATERCURRENTS_U",
#     unit_of_measure = "cm/s",
#     parameter_definition="Eastward velocity of water current in the water body",
#     seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/LCEWZZ01/",
#     seadatanet_unit_of_measure="SDN:P06::UVAA",
#     source_name="m_final_water_vx"
# )
#
# ALTITUDE = Parameter(
#     parameter_name = "ALTITUDE",
#      unit_of_measure = "m",
#      parameter_definition="Height (spatial coordinate) relative to bed surface in the water body",
#      seadatanet_parameter="	http://vocab.nerc.ac.uk/collection/P01/current/AHSFZZ01/",
#      seadatanet_unit_of_measure="SDN:P06::ULAA",
#      source_name="m_altitude"
# )


#
# LATITUDE_GPS = Parameter(
#     parameter_name = "LATITUDE_GPS",
#     standard_name="latitude_north_gps",
#     unit_of_measure = "degrees_north",
#     parameter_definition="Latitude north relative to WGS84 by unspecified GPS system",
#     seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/ALATGP01/",
#     seadatanet_unit_of_measure="SDN:P06::DEGN",
#     source_name="m_gps_lat",
#     valid_max=90.00,
#     valid_min=-90.00,
#     ancillary_variables="LATITUDE_GPS_QC"
# )
#
