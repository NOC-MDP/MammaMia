Worlds = {
    "global_reanalysis_physics": {
        "source": "CMEMS",
        "datasets": {
            "cmems_mod_glo_phy_my_0.083deg_P1D-m": {
                "variables": {
                    "temperature": "thetao",
                    "salinity": "so",
                    "ucomponent": "uo",
                    "vcomponent": "vo",
                }
            }
        },
        "extent": {
            "temporal": ["1993-01-01", "2021-07-07"],
            "spatial": [-180, 179.92, -80, 90],
            "levels": 50,
        },
        "type": "D-m",
        "forecast": False
    },

    "global_hindcast_biogeochemistry": {
        "source": "CMEMS",
        "datasets": {
            "cmems_mod_glo_bgc_my_0.25deg_P1D-m": {
                "variables": {
                    "chlorophyll": "chl",
                    "nitrate": "no3",
                    "phosphate": "po4",
                    "silicate": "si",
                    "dissolvedoxygen": "o2",
                    "netprimaryproduction": "nppv",
                }
            }
        },
        "extent": {
            "temporal": ["1993-01-01", "2022-12-01"],
            "spatial": [-180, 179.92, -80, 90],
            "levels": 75,
        },
        "type": "D-m",
        "forecast": False
    },

    "global_analysis_forecast_physics": {
        "source": "CMEMS",
        "datasets": {
            "cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m": {
                "variables": {
                    "temperature": "thetao",
                }
            },
            "cmems_mod_glo_phy-so_anfc_0.083deg_P1D-m": {
                "variables": {
                    "salinity": "so",
                }
            },
            "cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m": {
                "variables": {
                    "ucomponent": "uo",
                    "vcomponent": "vo",
                }
            }
        },
        "extent": {
            "temporal": ["-2Y", "+10D"],
            "spatial": [-180, 179.92, -80, 90],
            "levels": 50,
        },
        "type": "D-m",
        "forecast": True
    },

    "global_analysis_forecast_biogeochemistry": {
        "source": "CMEMS",
        "datasets": {
            "cmems_mod_glo_bgc-nut_anfc_0.25deg_P1D-m": {
                "variables": {
                    "nitrate": "no3",
                    "phosphate": "po4",
                    "dissolvediron": "fe",
                    "dissolvedsilicate": "si"
                }
            },
            "cmems_mod_glo_bgc-bio_anfc_0.25deg_P1D-m": {
                "variables": {
                    "netprimaryproduction": "nppv",
                    "dissolvedoxygen": "o2",
                }
            },
            "cmems_mod_glo_bgc-car_anfc_0.25deg_P1D-m": {
                "variables": {
                    "totalalkalinity": "talk",
                    "dissolvedinorganiccarbon": "dissic",
                    "pH": "ph"
                }
            },
            "cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m": {
                "variables": {
                    "totalchlorophyll": "chl",
                    "totalphytoplankton": "phyc"
                }
            },
            "cmems_mod_glo_bgc-optics_anfc_0.25deg_P1D-m": {
                "variables": {
                    "coefficentoflight": "kd"
                }
            }

        },
        "extent": {
            "temporal": ["-2Y", "+10D"],
            "spatial": [-180, 179.92, -80, 90],
            "levels": 50,
        },
        "type": "D-m",
        "forecast": True
    },
}
