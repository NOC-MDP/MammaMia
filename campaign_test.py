from mamma_mia import Campaign
from mamma_mia import Creator, Publisher, Contributor
from mamma_mia import inventory


print(f"Available groups in inventory {inventory.list_inventory_groups()}")
print(f"Available platform types: {inventory.list_platform_types()}")
print(f"Available platforms of type slocum: {inventory.list_platforms(platform_type='slocum')}")
print(f"Available parameters: {inventory.list_parameters()}")
print(f"Available sensor types: {inventory.list_sensor_types()}")
print(f"Parameters Alias: {inventory.list_parameter_aliases()}")
print(f"Parameter Info: {inventory.get_parameter_info(parameter_ref='salinity')}")
print(f"Platform Info: {inventory.get_platform_info(platform_ref='Cheesy')}")
print(f"sensors of type CTD: {inventory.list_sensors(sensor_type='CTD')}")
print(f"sensor info: {inventory.get_sensor_info(sensor_ref='SBE Glider Payload CTD 9099')}")

print("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# create campaign
campaign = Campaign(name="RAPID array virtual mooring",
                    description="single slocum glider deployment at a RAPID mooring",
                    verbose=True
                    )

print(f"sources available: {campaign.catalog.get_sources_list()}")
campaign.catalog.set_priority(source="MSM",priority=3)
print(f"sources available: {campaign.catalog.get_sources_list()}")

# create platform entity (mutable)
Churchill_withCTD = inventory.create_platform_entity(entity_name="Churchill_withCTD",platform="Churchill")

# list compatible sensors for entity of type CTD
availableCTD = Churchill_withCTD.list_compatible_sensors(sensor_type="CTD")
#print the sensor names and serial numbers
print(availableCTD)
availableSensors = Churchill_withCTD.list_compatible_sensors()
print(availableSensors)

# create sensor entity (mutable)
glider_CTD = inventory.create_sensor_entity(entity_name="ctd_for_churchill",sensor_ref=availableCTD["CTD"][0]["serial_number"])
# register sensor to platform
Churchill_withCTD.register_sensor(sensor=glider_CTD)
# create new entity of same platform this one doesn't have a CTD
Churchill_noCTD = inventory.create_platform_entity(entity_name="Churchill_noCTD",platform="Churchill")

# ALR4 = inventory.create_platform_entity(entity_name="ALR4",platform="ALR_4")
# ALR_ctd = inventory.create_sensor_entity(entity_name="ALR_ctd",sensor_ref="0221")
# ALR_ctd.update_sample_rate(sample_rate=60)
# ALR4.register_sensor(sensor=ALR_ctd)

# register platforms to the campaign for use in missions
campaign.register_platform(entity=Churchill_withCTD)
# campaign.register_platform(entity=ALR4)

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

# # add mission
campaign.add_mission(mission_name="RAD24_01",
                     title="Churchill with CTD deployment at RAPID array mooring eb1l2n",
                     summary="single glider deployed to perform a virtual mooring flight at the eb1l2n RAPID array.",
                     platform_name="Churchill_withCTD",
                     trajectory_path="data/waypoints/waypoints.nc",
                     creator=creator,
                     publisher=publisher,
                     contributor=contributor,
                     source_location="rapid_data",
                     mission_time_step=60)


# Set interpolators to automatically cache as dat files (no need to regenerate them, useful for large worlds)
#campaign.enable_interpolator_cache()

# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()

# run/fly missions
campaign.run()

# visualise the results
# colourmap options are here https://plotly.com/python/builtin-colorscales/
campaign.missions["RAD24_01"].plot_trajectory()
#campaign.missions["RAD24_02"].plot_trajectory()
campaign.missions["RAD24_01"].show_payload()
#campaign.missions["RAD24_02"].show_payload(parameter="TEMP")
campaign.export()
print("the end")

