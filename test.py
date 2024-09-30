
from mamma_mia import Slocum, sensors, Campaign
from loguru import logger


logger.info("starting Mamma Mia test run")
# create AUV
glider = Slocum(set_id="Slocum_1")
# define sensors
glider.add_sensor_arrays(sensor_array_list=[sensors.CTD(),sensors.BIO()])
# create campaign
campaign = Campaign(name="campaign_1",description="single slocum glider deployment in North sea 2019")
# add mission
campaign.add_mission(name="mission_1",
                     description="slocum glider Slocum_1 in the North Sea 2019",
                     auv=glider,
                     trajectory_path="comet-mm1.nc")
# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()
# run/fly missions
campaign.run()
# # visualise the results
# # colourmap options are here https://plotly.com/python/builtin-colorscales/
campaign.missions["mission_1"].plot_trajectory()
campaign.missions["mission_1"].show_reality(parameter="temperature")
campaign.missions["mission_1"].show_reality(parameter="salinity",colourscale="haline")
campaign.missions["mission_1"].show_reality(parameter="phosphate",colourscale="algae")
# export the campaign
campaign.export()

logger.success("Mamma Mia test complete")

def test_glider():
    assert campaign.missions["mission_1"].auv.type == "Slocum"
