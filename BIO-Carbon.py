# This script creates an payload emulation of the BIO-Carbon Deployment

from mamma_mia import Campaign
from mamma_mia import Creator, Publisher, Contributor
from mamma_mia import inventory

# create campaign
campaign = Campaign(name="BIO-Carbon",
                    description="This campaign involves the deployment of two Autosub Long Range (ALR) and four gliders "
                                "in the Iceland Basin under the Biological Influence on Future Ocean Storage of Carbon "
                                "(BIO-Carbon) programme, funded by a Natural Environment Research Council (NERC) "
                                "Strategic Research Grant. The gliders were deployed May 2024 and the ALRs were deployed"
                                " in June 2024, with the gliders being deployed from and recovered by the RRS Discovery "
                                "(DY180) alongside four Argo floats, and the ALRs being shore launched.",
                    verbose=True
                    )


# create platform entities
Churchill = inventory.create_platform_entity(entity_name="Churchill",platform="Churchill")
Nelson = inventory.create_platform_entity(entity_name="Nelson",platform="Nelson")
Doombar = inventory.create_platform_entity(entity_name="Doombar",platform="Doombar")
Cabot = inventory.create_platform_entity(entity_name="Cabot",platform="Cabot")
ALR4 = inventory.create_platform_entity(entity_name="ALR4",platform="ALR_4")
ALR6 = inventory.create_platform_entity(entity_name="ALR6",platform="ALR_6")


# create CTD payloads
ChurchillCTD = inventory.create_sensor_entity(entity_name="ctd_for_churchill",sensor_ref="9100")
NelsonCTD = inventory.create_sensor_entity(entity_name="ctd_for_nelson",sensor_ref="9099")
ALR4CTD = inventory.create_sensor_entity(entity_name="ctd_for_ALR4",sensor_ref="0221")

# create florescence payloads
ChurchillFluor = inventory.create_sensor_entity(entity_name="fluor_for_churchill",sensor_ref="3289")
NelsonFluor = inventory.create_sensor_entity(entity_name="fluor_for_nelson",sensor_ref="1611")


# create dissolved gas payloads
ChurchillDissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_churchill",sensor_ref="286")
NelsonDissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_nelson",sensor_ref="144")


# create PAR payloads
ChurchillPAR = inventory.create_sensor_entity(entity_name="par_for_churchill",sensor_ref="461")
NelsonPAR = inventory.create_sensor_entity(entity_name="par_for_nelson",sensor_ref="459")


# register sensors to platforms
Churchill.register_sensor(sensor=ChurchillCTD)
Churchill.register_sensor(sensor=ChurchillFluor)
Churchill.register_sensor(sensor=ChurchillPAR)
Churchill.register_sensor(sensor=ChurchillDissolvedGas)
ALR4.register_sensor(sensor=ALR4CTD)

# register platforms to the campaign for use in missions
campaign.register_platform(entity=Churchill)
campaign.register_platform(entity=Nelson)
campaign.register_platform(entity=Doombar)
campaign.register_platform(entity=Cabot)
campaign.register_platform(entity=ALR4)
campaign.register_platform(entity=ALR6)

# for metadata purposes a creator can be specified
creator = Creator(email="thopri@noc.ac.uk",
                  institution="NOCS",
                  name="thopri",
                  creator_type="",
                  url="noc.ac.uk")
# and a publisher
publisher = Publisher(email="glidersbodc@noc.ac.uk",
                      institution="NOCS",
                      name="NOCS",
                      type="DAC",
                      url="bodc.ac.uk")

# and a contributor
contributor = Contributor(email="thopri@noc.ac.uk",
                          name="thopri",
                          role_vocab="BODC database",
                          role="Collaborator",)

# # # add mission
# campaign.add_mission(mission_name="RAD24_01",
#                      title="Churchill with CTD deployment at RAPID array mooring eb1l2n",
#                      summary="single glider deployed to perform a virtual mooring flight at the eb1l2n RAPID array.",
#                      platform_name="Churchill_withCTD",
#                      trajectory_path="data/waypoints/waypoints.nc",
#                      creator=creator,
#                      publisher=publisher,
#                      contributor=contributor,
#                      source_location="rapid_data",
#                      mission_time_step=60)

# # add mission
campaign.add_mission(mission_name="RAD24_02",
                     title="ALR simlulating BIOCARBON mission",
                     summary="single ALR mission from BIOCARBON",
                     platform_name="ALR4",
                     trajectory_path="ALR_4_649_R.nc",
                     creator=creator,
                     publisher=publisher,
                     contributor=contributor,
                     source_location="CMEMS",
                     mission_time_step=60)

# Set interpolators to automatically cache as dat files (no need to regenerate them, useful for large worlds)
#campaign.enable_interpolator_cache()

# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()

# run/fly missions
campaign.run()

# visualise the results
# colourmap options are here https://plotly.com/python/builtin-colorscales/
#campaign.missions["RAD24_01"].plot_trajectory()
campaign.missions["RAD24_02"].plot_trajectory()
#campaign.missions["RAD24_01"].show_payload()
campaign.missions["RAD24_02"].show_payload()
campaign.export()
print("the end")