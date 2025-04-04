from mamma_mia import Campaign
from mamma_mia import Creator, Publisher, Contributor
from mamma_mia import Inventory
from mamma_mia import SensorBehavior

print(Inventory.list_inventory_groups())# list platforms
print(f"Available platform types: {Inventory.list_platform_types()}")
print(f"Available platforms of type slocum: {Inventory.list_platforms(platform_type='slocum')}")

print("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# create campaign
campaign = Campaign(name="SE_Greenland_Aug_2024",
                    description="single slocum glider deployment off South East Greenland",
                    verbose=True
                    )

print(f"sources available: {campaign.catalog.get_sources_list()}")
campaign.catalog.set_priority(source="MSM",priority=3)
print(f"sources available: {campaign.catalog.get_sources_list()}")



# create platform entity (mutable)
Churchill_withCTD = Inventory.create_platform_entity(entity_name="Churchill_withCTD",platform="Churchill")

print(f"sensor types: {Inventory.list_sensor_types()}")

# list compatible sensors for entity of type CTD
availableCTD = Churchill_withCTD.list_compatible_sensors(sensor_type="CTD")
#print the sensor names and serial numbers
print(availableCTD)
availableSensors = Churchill_withCTD.list_compatible_sensors()
print(availableSensors)

# create sensor entity (mutable)
glider_CTD = Inventory.create_sensor_entity(entity_name="ctd_for_churchill",sensor_ref=availableCTD["CTD"][0]["serial_number"])
glider_CTD.update_sample_rate(sample_rate=10)
# register sensor to platform
Churchill_withCTD.register_sensor(sensor=glider_CTD)
# change sensor sampling to upcast only
Churchill_withCTD.sensor_behaviour = SensorBehavior.Upcast
# create new entity of same platform this one doesn't have a CTD
Churchill_noCTD = Inventory.create_platform_entity(entity_name="Churchill_noCTD",platform="Churchill")

# register platforms to the campaign for use in missions
campaign.register_platform(entity=Churchill_noCTD)
campaign.register_platform(entity=Churchill_withCTD)

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
campaign.add_mission(mission_name="SEG24_01",
                     title="Churchill with CTD deployment off South East Greenland in August 2024",
                     summary="single glider deployed to perform a virtual mooring flight at the eb1l2n RAPID array.",
                     platform_name="Churchill_withCTD",
                     trajectory_path="eb1l2n-spiral.nc",
                     creator=creator,
                     publisher=publisher,
                     contributor=contributor)

# Set interpolators to automatically cache as dat files (no need to regenerate them, useful for large worlds)
#campaign.enable_interpolator_cache()

# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()

# run/fly missions
campaign.run()

# visualise the results
# colourmap options are here https://plotly.com/python/builtin-colorscales/
campaign.missions["SEG24_01"].plot_trajectory()
campaign.missions["SEG24_01"].show_payload()
# export the campaign
campaign.export()
campaign.missions["SEG24_01"].export_to_nc()
print("the end")

