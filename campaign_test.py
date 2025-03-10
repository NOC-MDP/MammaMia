from loguru import logger
logger.info("<=========> preparing mamma mia catalogs <===========>")
from mamma_mia import sensors
from mamma_mia import platforms
from mamma_mia import Campaign
from pprint import pp
logger.success("<=========> Mamma Mia catalogs successfully created <===========>")
logger.info("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# create campaign
campaign = Campaign(name="campaign_1",
                    description="single slocum glider deployment in North sea 2019",
                    verbose=True
                    )
# # add AUV

ALR4_withCTD = platforms.get_platform(platform_name="ALR_4",platform_type="alr")
logger.info(f"sensor types availble {sensors.list_sensor_types()}")
pp(sensors.list_sensors(sensor_type="CTD"))
sensor = sensors.get_sensor(sensor_type="CTD",sensor_ref="0221")
ALR4_withCTD.register_sensor(sensor)

ALR4_noCTD = platforms.get_platform(platform_name="ALR_4",platform_type="alr")

campaign.register_platform(platform=ALR4_noCTD,name="ALR_4_noCTD")
campaign.register_platform(platform=ALR4_withCTD,name="ALR_4_withCTD")

print("the end")


# pp(campaign,depth=1)
# # add mission
# campaign.add_mission(name="mission_1",
#                      description="slocum glider Slocum_1 in the North Sea 2019",
#                      auv="Slocum_1",
#                      trajectory_path="comet-mm1.nc")
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
