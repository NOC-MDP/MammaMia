import json
from dataclasses import dataclass, field
from mamma_mia.exceptions import InvalidParameter


@dataclass(frozen=True)
class TimeParameter:
    long_name: str
    units: str
    standard_name: str
    valid_min: float
    valid_max: float
    calendar: str
    fill_value: float

TIME = TimeParameter(
    long_name="time of measurement and gps location",
    units="seconds since 1970-01-01 00:00:00Z",
    standard_name="time",
    valid_min=1000000000,
    valid_max=4000000000,
    calendar="gregorian",
    fill_value=-1.0
)

TIME_GPS = TimeParameter(
    long_name="time of ech gps locations",
    units="seconds since 1970-01-01 00:00:00Z",
    standard_name="",
    valid_min=1000000000,
    valid_max=4000000000,
    calendar="gregorian",
    fill_value=-1.0
)

@dataclass(frozen=True)
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

    def __post_init__(self):
        # TODO add more validation here
        if not isinstance(self.parameter_name, str):
            raise TypeError(f"parameter name must be an instance of str, got {type(self.bodc_platform_model_id)}")


@dataclass
class ParameterCatalog:
    environmental: dict[str, Parameter] = field(default_factory=dict)
    navigation: dict[str, Parameter] = field(default_factory=dict)

    def __post_init__(self):
        with open("src/mamma_mia/parameters.json", "r") as f:
            params = json.load(f)

        for parameter_type, parameters in params["parameters"].items():
            if parameter_type =="environmental":
                for parameter in parameters:
                    try:
                        self.environmental[parameter["parameter_name"]] = Parameter(**parameter)
                    except KeyError:
                        raise InvalidParameter(f"{parameter['parameter_name']} is not a valid parameter")
            if parameter_type =="navigation":
                for parameter in parameters:
                    try:
                        self.navigation[parameter["parameter_name"]] = Parameter(**parameter)
                    except KeyError:
                        raise InvalidParameter(f"{parameter['parameter_name']} is not a valid parameter")
parameters = ParameterCatalog()

# CHLA = Parameter(
#     parameter_name = "CHLA",
#     standard_name = "mass_concentration_of_chlorophyll_a_in_sea_water",
#     unit_of_measure = "mg/m3",
#     parameter_definition = "Concentration of chlorophyll-a {chl-a CAS 479-61-8} per unit volume of the water body [particulate >unknown phase] by in-situ chlorophyll fluorometer",
#     seadatanet_parameter= "http://vocab.nerc.ac.uk/collection/P01/current/CPHLPR01/",
#     seadatanet_unit_of_measure = "SDN:P06::UMMC",
#     source_name = "sci_flbbcd_chlor_units",
#     ancillary_variables = "CHLA_QC",
# )

# CDOM = Parameter(
#     parameter_name = "CDOM",
#      unit_of_measure = "ppb",
#      parameter_definition="Concentration of coloured dissolved organic matter {CDOM Gelbstoff} per unit volume of the water body [dissolved plus reactive particulate phase] by in-situ WET Labs FDOM ECO fluorometer",
#      seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/CCOMD002/",
#      seadatanet_unit_of_measure="SDN:P06::UPPB",
#      source_name="sci_flbbcd_cdom_units"
# )

# BBP700 = Parameter(
#     parameter_name = "BBP700",
#     standard_name = "",
#     unit_of_measure = "m-1",
#     parameter_definition="Attenuation due to backscatter (700 nm wavelength at 117 degree incidence) by the water body [particulate >unknown phase] by in-situ optical backscatter measurement",
#     seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/BB117NIR/",
#     seadatanet_unit_of_measure="SDN:P06::UUUU",
#     source_name="sci_flbbcd_bb_units",
#     ancillary_variables="BBP700_QC",
# )

# TEMP_DOXY = Parameter(
#     parameter_name = "TEMP_DOXY",
#       unit_of_measure = "degree_Celsius",
#       parameter_definition="Temperature of oxygen determination by optode",
#       seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/OXYTAAOP/",
#       seadatanet_unit_of_measure="SDN:P06::UPAA",
#       source_name="sci_oxy4_temp"
# )
#
# ALR_Latitude = Parameter(
#     parameter_name = "",
#      unit_of_measure = "",
#      parameter_definition="Latitude north of measurement platform in the water body by estimation using best available on-board navigation system and algorithm",
#      seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/ALATPT01/",
#      seadatanet_unit_of_measure="SDN:P06::UAAA",
#      source_name="Latitude"
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

# LATITUDE = Parameter(
#     parameter_name = "LATITUDE",
#     standard_name="latitude_north",
#     unit_of_measure = "degrees_north",
#     parameter_definition="Latitude north",
#     seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/ALATZZ01/",
#     seadatanet_unit_of_measure="SDN:P06::DEGN",
#     source_name="m_lat",
#     valid_max=90.00,
#     valid_min=-90.00,
#     ancillary_variables="LATITUDE_QC"
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
