# from mamma_mia import Campaign, Slocum, CTD, BIO
from mamma_mia import Extent,Point,VelocityReality

print("<=========> starting Mamma Mia test run <===========>")
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
# # build missions (search datasets, download datasets, build interpolators etc)
# campaign.build_missions()
# # run/fly missions
# campaign.run()
# # # visualise the results
# # # colourmap options are here https://plotly.com/python/builtin-colorscales/
# campaign.missions["mission_1"].plot_trajectory()
# campaign.missions["mission_1"].show_reality(parameter="temperature")
# campaign.missions["mission_1"].show_reality(parameter="salinity",colour_scale="haline")
# campaign.missions["mission_1"].show_reality(parameter="phosphate",colour_scale="algae")
# # export the campaign
# campaign.export()
extent = Extent(max_lat=58.0,
                min_lat=56.0,
                min_lng=6.0,
                max_lng=7.0,
                max_depth=200,
                start_dt="2019-01-01T00:00:00",
                end_dt="2019-01-07T00:00:00"
                )
point = Point(latitude=57.1,
              longitude=6.4,
              depth=12.0,
              dt="2019-01-03T00:00:00",

)
VR = VelocityReality(extent=extent)
V = VR.teleport(point=point)
print(V)
print(">===========< Mamma Mia test complete >==========<")

# def test_glider():
#     assert campaign.missions["mission_1"].auv.type == "Slocum"
