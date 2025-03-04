from dataclasses import dataclass


@dataclass(frozen=True)
class Parameter:
    parameter_name: str
    unit_of_measure: str
    parameter_definition: str
    seadatanet_parameter: str
    seadatanet_unit_of_measure: str
    source_name: str

CNDC = Parameter(parameter_name = "CNDC",
                 unit_of_measure = "mhos/m",
                 parameter_definition = "Electrical conductivity of the water body by CTD",
                 seadatanet_parameter = "http://vocab.nerc.ac.uk/collection/P01/current/CNDCST01/",
                 seadatanet_unit_of_measure = "SDN:P06::UECA",
                 source_name = "sci_water_cond"
                 )

PRES = Parameter(parameter_name = "PRES",
                 unit_of_measure = "decibar",
                 parameter_definition = "Pressure (spatial coordinate) exerted by the water body by profiling pressure sensor and correction to read zero at sea level",
                 seadatanet_parameter = "http://vocab.nerc.ac.uk/collection/P01/current/PRESPR01/",
                 seadatanet_unit_of_measure = "SDN:P06::UPDB",
                 source_name = "sci_water_pressure"
                 )

TEMP = Parameter(parameter_name =  "TEMP",
                 unit_of_measure = "degree_Celsius",
                 parameter_definition = "Temperature of the water body by CTD or STD",
                 seadatanet_parameter = "http://vocab.nerc.ac.uk/collection/P01/current/TEMPST01/",
                 seadatanet_unit_of_measure = "SDN:P06::UPAA",
                 source_name = "sci_water_temp"
                 )

CHLA = Parameter(parameter_name = "CHLA",
                 unit_of_measure = "mg/m3",
                 parameter_definition = "Concentration of chlorophyll-a {chl-a CAS 479-61-8} per unit volume of the water body [particulate >unknown phase] by in-situ chlorophyll fluorometer",
                 seadatanet_parameter= "http://vocab.nerc.ac.uk/collection/P01/current/CPHLPR01/",
                 seadatanet_unit_of_measure = "SDN:P06::UMMC",
                 source_name = "sci_flbbcd_chlor_units"
                 )

CDOM = Parameter(parameter_name = "CDOM",
                 unit_of_measure = "ppb",
                 parameter_definition="Concentration of coloured dissolved organic matter {CDOM Gelbstoff} per unit volume of the water body [dissolved plus reactive particulate phase] by in-situ WET Labs FDOM ECO fluorometer",
                 seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/CCOMD002/",
                 seadatanet_unit_of_measure="SDN:P06::UPPB",
                 source_name="sci_flbbcd_cdom_units"
                 )

BBP700 = Parameter(parameter_name = "BBP700",
                   unit_of_measure = "m-1",
                   parameter_definition="Attenuation due to backscatter (700 nm wavelength at 117 degree incidence) by the water body [particulate >unknown phase] by in-situ optical backscatter measurement",
                   seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/BB117NIR/",
                   seadatanet_unit_of_measure="	SDN:P06::UUUU",
                   source_name="sci_flbbcd_bb_units"
                   )

TEMP_DOXY = Parameter(parameter_name = "TEMP_DOXY",
                      unit_of_measure = "degree_Celsius",
                      parameter_definition="Temperature of oxygen determination by optode",
                      seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/OXYTAAOP/",
                      seadatanet_unit_of_measure="SDN:P06::UPAA",
                      source_name="sci_oxy4_temp"
                      )

ALR_Latitude = Parameter(parameter_name = "",
                         unit_of_measure = "",
                         parameter_definition="Latitude north of measurement platform in the water body by estimation using best available on-board navigation system and algorithm",
                         seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/ALATPT01/",
                         seadatanet_unit_of_measure="SDN:P06::UAAA",
                         source_name="Latitude"
                         )

LATITUDE = Parameter(parameter_name = "LATITUDE",
                         unit_of_measure = "degrees_north",
                         parameter_definition="Latitude north",
                         seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/ALATZZ01/",
                         seadatanet_unit_of_measure="SDN:P06::DEGN",
                         source_name="m_lat"
                     )

WATERCURRENTS_U = Parameter(parameter_name = "WATERCURRENTS_U",
                            unit_of_measure = "cm/s",
                            parameter_definition="Eastward velocity of water current in the water body",
                            seadatanet_parameter="http://vocab.nerc.ac.uk/collection/P01/current/LCEWZZ01/",
                            seadatanet_unit_of_measure="SDN:P06::UVAA",
                            source_name="m_final_water_vx"
                            )

ALTITUDE = Parameter(parameter_name = "ALTITUDE",
                     unit_of_measure = "m",
                     parameter_definition="Height (spatial coordinate) relative to bed surface in the water body",
                     seadatanet_parameter="	http://vocab.nerc.ac.uk/collection/P01/current/AHSFZZ01/",
                     seadatanet_unit_of_measure="SDN:P06::ULAA",
                     source_name="m_altitude"
                     )

