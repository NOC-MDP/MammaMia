from mamma_mia import Mission, Slocum, sensors, Campaign, SensorSuite
# create AUV
slocum = Slocum(id="Slocum_1",sensorsuite=SensorSuite({"array_1": sensors.CTD(),"array_2":sensors.BIO()}),)
#create empty mission
mission = Mission(name= "mission_1", description="flight of the conchords")
# populate mission
mission.create_mission(auv=slocum,traj_path="comet-mm1.nc")
# plot trajectory
mission.trajectory.plot_trajectory()
#create empty campaign
campaign = Campaign(name="example campaign", description="single slocum glider flight in the North Sea")
#add mission to it
campaign.add_mission(mission=mission)
# run the campaign
campaign.run()
# visualise the results
# colourmap options are here https://plotly.com/python/builtin-colorscales/
campaign.missions["mission_1"].show_reality(parameter="temperature")
campaign.missions["mission_1"].show_reality(parameter="salinity",colourscale="haline")
campaign.missions["mission_1"].show_reality(parameter="phosphate",colourscale="algae")

def test_glider():
    assert mission.auv.type == "Slocum"
