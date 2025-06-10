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


# create CTD sensors
ChurchillCTD = inventory.create_sensor_entity(entity_name="ctd_for_churchill",sensor_ref="9100")
NelsonCTD = inventory.create_sensor_entity(entity_name="ctd_for_nelson",sensor_ref="9099")
DoombarCTD = inventory.create_sensor_entity(entity_name="ctd_for_doombar",sensor_ref="9140")
CabotCTD = inventory.create_sensor_entity(entity_name="ctd_for_cabobot",sensor_ref="9110")
ALR4CTD = inventory.create_sensor_entity(entity_name="ctd_for_ALR4",sensor_ref="0221")
ALR6CTD = inventory.create_sensor_entity(entity_name="ctd_for_ALR6",sensor_ref="0222")

# create florescence sensors
ChurchillFluor = inventory.create_sensor_entity(entity_name="fluor_for_churchill",sensor_ref="3289")
NelsonFluor = inventory.create_sensor_entity(entity_name="fluor_for_nelson",sensor_ref="1611")
DoombarFluor = inventory.create_sensor_entity(entity_name="fluor_for_doombar",sensor_ref="3352")
ALR4Fluor = inventory.create_sensor_entity(entity_name="fluor_for_ALR4",sensor_ref="8579")
ALR6Fluor = inventory.create_sensor_entity(entity_name="fluor_for_ALR6",sensor_ref="8597")
CabotFluor = inventory.create_sensor_entity(entity_name="fluor_for_cabobot",sensor_ref="3325")

# create dissolved gas sensors
ChurchillDissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_churchill",sensor_ref="286")
NelsonDissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_nelson",sensor_ref="144")
DoombarDissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_doombar",sensor_ref="143")
ALR4DissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_ALR4",sensor_ref="4513")
ALR6DissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_ALR6",sensor_ref="4301")
CabotDissolvedGas = inventory.create_sensor_entity(entity_name="dissolved_gas_for_cabobot",sensor_ref="119")

# create PAR sensors
ChurchillPAR = inventory.create_sensor_entity(entity_name="par_for_churchill",sensor_ref="461")
NelsonPAR = inventory.create_sensor_entity(entity_name="par_for_nelson",sensor_ref="459")


# register sensors to platform entities
Churchill.register_sensor(sensor=ChurchillCTD)
Churchill.register_sensor(sensor=ChurchillFluor)
Churchill.register_sensor(sensor=ChurchillPAR)
Churchill.register_sensor(sensor=ChurchillDissolvedGas)

Nelson.register_sensor(sensor=NelsonCTD)
Nelson.register_sensor(sensor=NelsonFluor)
Nelson.register_sensor(sensor=NelsonPAR)
Nelson.register_sensor(sensor=NelsonDissolvedGas)

Doombar.register_sensor(sensor=DoombarCTD)
Doombar.register_sensor(sensor=DoombarFluor)
Doombar.register_sensor(sensor=DoombarDissolvedGas)

ALR4.register_sensor(sensor=ALR4CTD)
ALR4.register_sensor(sensor=ALR4Fluor)
ALR4.register_sensor(sensor=ALR4DissolvedGas)

ALR6.register_sensor(sensor=ALR6CTD)
ALR6.register_sensor(sensor=ALR6Fluor)
ALR6.register_sensor(sensor=ALR6DissolvedGas)

Cabot.register_sensor(sensor=CabotCTD)
Cabot.register_sensor(sensor=CabotFluor)
Cabot.register_sensor(sensor=CabotDissolvedGas)


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

# add Churchill mission currently commented out due to Churchill missing depth data.
# campaign.add_mission(mission_name="Deployment 647",
#                      title="Churchill BIO-Carbon deployment",
#                      summary="Churchill's mission that it undertook during BIO-Carbon",
#                      platform_name="Churchill",
#                      trajectory_path="BioCarbonTrajectories/Churchill_647_R.nc",
#                      creator=creator,
#                      publisher=publisher,
#                      contributor=contributor,
#                      source_location="CMEMS",
#                      mission_time_step=60)

# # add Nelson mission
campaign.add_mission(mission_name="Deployment 646",
                     title="Nelson BIO-Carbon deployment",
                     summary="Nelsons's mission that it undertook during BIO-Carbon",
                     platform_name="Nelson",
                     trajectory_path="BioCarbonTrajectories/Nelson_646_R.nc",
                     creator=creator,
                     publisher=publisher,
                     contributor=contributor,
                     source_location="CMEMS",
                     mission_time_step=60)

# # add Doombar mission
campaign.add_mission(mission_name="Deployment 648",
                     title="Doombar BIO-Carbon deployment",
                     summary="Doombar's mission that it undertook during BIO-Carbon",
                     platform_name="Doombar",
                     trajectory_path="BioCarbonTrajectories/Doombar_648_R.nc",
                     creator=creator,
                     publisher=publisher,
                     contributor=contributor,
                     source_location="CMEMS",
                     mission_time_step=60)

# # add ALR4 mission
campaign.add_mission(mission_name="Deployment 649",
                     title="ALR4 BIO-Carbon deployment",
                     summary="ALR4's mission that it undertook during BIO-Carbon",
                     platform_name="ALR4",
                     trajectory_path="BioCarbonTrajectories/ALR_4_649_R.nc",
                     creator=creator,
                     publisher=publisher,
                     contributor=contributor,
                     source_location="CMEMS",
                     mission_time_step=60)

# # add ALR6 mission
campaign.add_mission(mission_name="Deployment 650",
                     title="ALR6 BIO-Carbon deployment",
                     summary="ALR6's mission that it undertook during BIO-Carbon",
                     platform_name="ALR6",
                     trajectory_path="BioCarbonTrajectories/ALR_6_650_R.nc",
                     creator=creator,
                     publisher=publisher,
                     contributor=contributor,
                     source_location="CMEMS",
                     mission_time_step=60)

# # add Cabot mission
campaign.add_mission(mission_name="Deployment 645",
                     title="Cabot BIO-Carbon deployment",
                     summary="Cabot's mission that it undertook during BIO-Carbon",
                     platform_name="Cabot",
                     trajectory_path="BioCarbonTrajectories/Cabot_645_R.nc",
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
campaign.missions["Deployment 650"].plot_trajectory()
#campaign.missions["RAD24_01"].show_payload()
campaign.missions["Deployment 650"].show_payload()
campaign.export()
print("the end")