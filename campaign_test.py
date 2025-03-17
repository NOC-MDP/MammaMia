from mamma_mia import platform_inventory
from mamma_mia import Campaign
from mamma_mia import sensor_inventory
from pprint import pp
print("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# create campaign
campaign = Campaign(name="Greenland_2028",
                    description="single slocum glider deployment off South East Greenland",
                    verbose=True
                    )
# # add AUV
pp(f"Availble platform types: {platform_inventory.list_platform_types()}")
pp(f"Availble platforms of type glider: {platform_inventory.list_platforms(platform_type='glider')}")
Churchill_withCTD = platform_inventory.create_entity(entity_name="Churchill_withCTD",platform="Churchill",platform_type="glider")

availableCTD = Churchill_withCTD.list_compatible_sensors(sensor_type="CTD")
availableRadiometers = Churchill_withCTD.list_compatible_sensors(sensor_type="radiometers")

glider_CTD = sensor_inventory.create_entity(entity_name="ctd_for_churchill",sensor_type="CTD",sensor_ref="9100")
glider_CTD.update_sample_rate(sample_rate=60)
Churchill_withCTD.register_sensor(sensor=glider_CTD)

Churchill_noCTD = platform_inventory.create_entity(entity_name="Churchill_noCTD",platform="Churchill",platform_type="glider")
Churchill_noCTD.toggle_sensor_coupling()
Churchill_noCTD.update_sensor_behaviour(sensor_behaviour="60_seconds_upcast")
campaign.register_platform(platform=Churchill_noCTD,name="Churchill_noCTD")
campaign.register_platform(platform=Churchill_withCTD,name="Churchill_withCTD")

# # add mission
campaign.add_mission(name="GL28_01",
                     description="Churchill with CTD deployment off South East Greenland",
                     platform_name="Churchill_withCTD",
                     trajectory_path="comet-mm1.nc")

campaign.init_catalog()

print("the end")
# # Set interpolators to automatically cache as dat files (no need to regenerate them, useful for large worlds)
# #campaign.enable_interpolator_cache()
# # build missions (search datasets, download datasets, build interpolators etc)
# campaign.build_missions()
# # run/fly missions
# campaign.run()
# # # visualise the results
# # # colourmap options are here https://plotly.com/python/builtin-colorscales/
# # campaign.missions["mission_1"].plot_trajectory()
# campaign.missions["mission_1"].show_reality()
# # export the campaign
# campaign.export()
#
# print(">===========< Mamma Mia AUV campaign test complete >==========<")
#
# def test_glider():
#     assert campaign.missions["mission_1"].auv.type == "Slocum"
