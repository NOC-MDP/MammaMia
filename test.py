from mamma_mia import Campaign
from loguru import logger

logger.info("starting Mamma Mia test run")
# create campaign
campaign = Campaign(name="campaign_1",
                    description="single slocum glider deployment in North sea 2019",
                    verbose=True
                    )
# print available auv's and sensor arrays
logger.info(campaign.list_auv_types())
logger.info(campaign.list_sensor_arrays())
# add AUV
campaign.add_auv(id="Slocum_1",
                 type="slocum",
                 sensor_arrays=["CTD","BIO"],
                 )
# add missions
campaign.add_mission(name="mission_1",
                     description="slocum glider Slocum_1 in the North Sea 2019",
                     auv="Slocum_1",
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
