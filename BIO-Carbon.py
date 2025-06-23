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


# create platform entities as the trajectory is from processed output for the gliders NMEA_conversion should be false
Churchill = inventory.create_platform_entity(entity_name="Churchill",
                                             platform="Slocum_G2",
                                             serial_number="unit_398",
                                             NMEA_conversion=False)
Nelson = inventory.create_platform_entity(entity_name="Nelson",
                                          platform="Slocum_G2",
                                          serial_number="unit_397",
                                          NMEA_conversion=False)
Doombar = inventory.create_platform_entity(entity_name="Doombar",
                                           platform="Slocum_G2",
                                           serial_number="unit_405",
                                           NMEA_conversion=False)
Cabot = inventory.create_platform_entity(entity_name="Cabot",
                                         platform="Slocum_G2",
                                         serial_number="unit_345",
                                         NMEA_conversion=False)
ALR4 = inventory.create_platform_entity(entity_name="ALR4",
                                        platform="ALR_1500",
                                        serial_number="ALR_4")
ALR6 = inventory.create_platform_entity(entity_name="ALR6",
                                        platform="ALR_1500",
                                        serial_number="ALR_6")

# register sensors to platform entities
Churchill.register_sensor(sensor_type="CTD")
Churchill.register_sensor(sensor_type="radiometer")
Churchill.register_sensor(sensor_type="dissolved_gas")

Nelson.register_sensor(sensor_type="CTD")
Nelson.register_sensor(sensor_type="radiometer")
Nelson.register_sensor(sensor_type="dissolved_gas")

Doombar.register_sensor(sensor_type="CTD")
Doombar.register_sensor(sensor_type="radiometers")
Doombar.register_sensor(sensor_type="dissolved_gas")

ALR4.register_sensor(sensor_type="CTD")
ALR4.register_sensor(sensor_type="radiometer")
ALR4.register_sensor(sensor_type="optical_backscatter")

ALR6.register_sensor(sensor_type="CTD")
ALR6.register_sensor(sensor_type="radiometer")
ALR6.register_sensor(sensor_type="optical_backscatter")


Cabot.register_sensor(sensor_type="CTD")
Cabot.register_sensor(sensor_type="radiometer")
Cabot.register_sensor(sensor_type="dissolved_gas")


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
# campaign.add_mission(mission_name="Deployment_647",
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
campaign.add_mission(mission_name="Deployment_646",
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
campaign.add_mission(mission_name="Deployment_648",
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
campaign.add_mission(mission_name="Deployment_649",
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
campaign.add_mission(mission_name="Deployment_650",
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
campaign.add_mission(mission_name="Deployment_645",
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
campaign.missions["Deployment_646"].plot_trajectory()
campaign.missions["Deployment_646"].show_payload(parameter="DOWNWELLING_RADIATIVE_FLUX")
campaign.export()
print("the end")