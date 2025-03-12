
print("<=========> preparing mamma mia catalogs <===========>")
from mamma_mia import sensors
from mamma_mia import platforms
from mamma_mia import Campaign
from pprint import pp
print("<=========> Mamma Mia catalogs successfully created <===========>")
print("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# create campaign
campaign = Campaign(name="Greenland_2028",
                    description="single slocum glider deployment off South East Greenland",
                    verbose=True
                    )
# # add AUV
pp(platforms.list_platform_types())
pp(platforms.list_platforms(platform_type="glider"))
Churchill_withCTD = platforms.get_platform(platform_name="Churchill",platform_type="glider")
# TODO link available sensors to selected platform? e.g. a list sensors method on the platform class?
print(f"sensor types available {sensors.list_sensor_types()}")
pp(sensors.list_sensors(sensor_type="CTD"))
sensor = sensors.get_sensor(sensor_type="CTD",sensor_ref="9100")
Churchill_withCTD.register_sensor(sensor)

Churchill_noCTD = platforms.get_platform(platform_name="Churchill",platform_type="glider")

campaign.register_platform(platform=Churchill_noCTD,name="Churchill_noCTD")
campaign.register_platform(platform=Churchill_withCTD,name="Churchill_withCTD")

# # add mission
campaign.add_mission(name="GL28_01",
                     description="slocum glider Slocum_1 in the North Sea 2019",
                     platform_name="Churchill_withCTD",
                     trajectory_path="comet-mm1.nc")

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
