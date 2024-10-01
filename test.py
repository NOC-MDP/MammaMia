from mamma_mia import AUV,Campaign,CTD,BIO,Slocum
from loguru import logger
import sys

# reset logger
logger.remove()
quiet = False
# set logger based on requested verbosity
if quiet:
    logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}', level="WARNING")
else:
    logger.add(sys.stdout, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}', level="INFO")

logger.info("starting Mamma Mia test run")
# create AUV
glider = AUV(id="Slocum_1",type=Slocum())
# define sensors
glider.add_sensor_arrays(sensor_arrays=[CTD(),BIO()])
# create campaign
campaign = Campaign(name="campaign_1",description="single slocum glider deployment in North sea 2019")
# add missions
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
campaign.missions["mission_1"].show_reality(parameter="salinity",colour_scale="haline")
campaign.missions["mission_1"].show_reality(parameter="phosphate",colour_scale="algae")
# export the campaign
campaign.export()

logger.success("Mamma Mia test complete")

def test_glider():
    assert campaign.missions["mission_1"].auv.type == "Slocum"
