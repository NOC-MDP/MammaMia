from mamma_mia import GliderMissionBuilder

sim = GliderMissionBuilder.virtual_mooring(
    mission_name="rapid-mooring",
    datetime_str="2023-03-03T12:00:00:Z",
    description="RAPID ARRAY simulation",
    glider_model="DEEP",
    inital_heading=225,
    lat_ini=27.225,
    lon_ini=-15.4225,
    glider_name="comet",
    mission_directory="RAPID-mooring",
    dive_depth=1000
)

sim.run_mission()
sim.save_mission()