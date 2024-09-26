from mamma_mia import Mission, Slocum, sensors, Campaign
from loguru import logger
logger.info("starting Mamma Mia test run")
# create AUV
glider = Slocum(set_id="Slocum_1")
glider.add_sensor_arrays(sensor_array_list=[sensors.CTD(),sensors.BIO()])
#create empty mission
mission = Mission(name= "mission_1", description="flight of the conchords")
# populate mission
mission.populate_mission(auv=glider,traj_path="comet-mm1.nc")
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

campaign.missions["mission_1"].export()

logger.success("Mamma Mia test complete")

def test_glider():
    assert mission.auv.type == "Slocum"
