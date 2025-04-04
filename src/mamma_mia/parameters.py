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
class TimeParameter:
    parameter_name: str
    long_name: str
    units: str
    standard_name: str
    valid_min: float
    valid_max: float
    calendar: str
    fill_value: float
    alias: list[str]


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
    alias: list[str]
    fill_value: float = 99999.0
    valid_max: float = None
    valid_min: float = None



@frozen
class ParameterInventory:
    entries: dict[str,Parameter|TimeParameter] = field(factory=dict)

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
                self.entries[parameter["parameter_name"]] = (
                    structure(parameter,TimeParameter) if parameter_type == "time" else structure(parameter,Parameter)
                )
            except TypeError as e:
                logger.error(e)
                raise ValueError(f"{parameter['parameter_name']} is not a valid {parameter_type} parameter")
            logger.info(f"parameter {parameter['parameter_name']} registered successfully")

    def get_parameter(self,parameter_name: str):
        """Returns a copy of the requested parameter to prevent modification."""
        if parameter_name in self.entries:
            return copy.deepcopy(self.entries[parameter_name])
        raise KeyError(f"Parameter '{parameter_name}' not found in parameter inventory")

    def add_parameter(self,parameter: Parameter | TimeParameter):
        """Adds a new parameter, preventing modifications to existing ones."""
        if parameter.parameter_name in self.entries:
            raise AttributeError(f"Parameter '{parameter.parameter_name}' already exists and cannot be modified.")
        self.entries[parameter.parameter_name] = parameter

    def remove_parameter(self,parameter_name: str):
        """Removes a parameter from the catalog."""
        if parameter_name in self.entries:
            del self.entries[parameter_name]
        else:
            raise KeyError(f"Parameter '{parameter_name}' not found in parameter inventory")



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
