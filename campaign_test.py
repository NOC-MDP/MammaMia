from mamma_mia import platform_inventory
from mamma_mia import Campaign
from mamma_mia import sensor_inventory

print("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# create campaign
campaign = Campaign(name="Greenland_2028",
                    description="single slocum glider deployment off South East Greenland",
                    verbose=True
                    )
# list platforms
print(f"Available platform types: {platform_inventory.list_platform_types()}")
print(f"Available platforms of type glider: {platform_inventory.list_platforms(platform_type='glider')}")

# create platform entity (mutable)
Churchill_withCTD = platform_inventory.create_entity(entity_name="Churchill_withCTD",platform="Churchill",platform_type="glider")

# list compatible sensors for entity
availableCTD = Churchill_withCTD.list_compatible_sensors(sensor_type="CTD")
availableRadiometers = Churchill_withCTD.list_compatible_sensors(sensor_type="radiometers")

# create sensor entity (mutable)
glider_CTD = sensor_inventory.create_entity(entity_name="ctd_for_churchill",sensor_type="CTD",sensor_ref="9100")
glider_CTD.update_sample_rate(sample_rate=10)
# register sensor to platform
Churchill_withCTD.register_sensor(sensor=glider_CTD)

# create new entity of same platform this one doesn't have a CTD
Churchill_noCTD = platform_inventory.create_entity(entity_name="Churchill_noCTD",platform="Churchill",platform_type="glider")

# register platforms to the campaign for use in missions
campaign.register_platform(platform=Churchill_noCTD,name="Churchill_noCTD")
campaign.register_platform(platform=Churchill_withCTD,name="Churchill_withCTD")

# # add mission
campaign.add_mission(mission_name="GL28_01",
                     title="Churchill with CTD deployment off South East Greenland",
                     summary="single glider deployed to undertake 15 dives to 200m",
                     platform_name="Churchill_withCTD",
                     trajectory_path="comet-mm1.nc")

# initalise model catalogs
campaign.init_catalog()

# Set interpolators to automatically cache as dat files (no need to regenerate them, useful for large worlds)
#campaign.enable_interpolator_cache()

# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()

# run/fly missions
campaign.run()

# visualise the results
# colourmap options are here https://plotly.com/python/builtin-colorscales/
campaign.missions["GL28_01"].plot_trajectory()
campaign.missions["GL28_01"].show_payload()
# export the campaign
campaign.export()
print("the end")

