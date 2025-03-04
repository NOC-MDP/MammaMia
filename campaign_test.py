#from mamma_mia import Campaign, Slocum, CTD, BIO
from pprint import pp
from mamma_mia import platforms
from mamma_mia import sensors
print(platforms.availble())
auv1 = platforms.ALR4
sensor = sensors.SBE_52MP_CTD_0221
print(f"AUV is called {auv1.platform_name}")
print(f"Add sensor {sensor.sensor_name}")
auv1.add_sensor(key="Radiometer",sensor=sensor)
pp(auv1,depth=1)

# print("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# # create campaign
# campaign = Campaign(name="campaign_1",
#                     description="single slocum glider deployment in North sea 2019",
#                     verbose=True
#                     )
# # add AUV
# campaign.add_auv(id="Slocum_1",
#                  type=Slocum(),
#                  sensor_arrays=[CTD(),BIO()],
#                  )
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
