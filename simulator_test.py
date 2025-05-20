from mamma_mia import MissionBuilder

sim = MissionBuilder.create_mission(
    mission_name="RAD024",
    datetime_str="2024-01-01T00:00:00:Z",
    description="RAPID ARRAY simulation",
    glider_model="DEEP",
    inital_heading=225,
    lat_ini=27.225,
    lon_ini=-15.4225,
    glider_name="Churchill",
    mission_directory="data/RAPID-mooring",
)

sim.run()
sim.save()