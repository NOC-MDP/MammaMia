from mamma_mia import GliderMissionBuilder

virtual_mooring_spiral = GliderMissionBuilder.virtual_mooring(
    mission_name="rapid-mooring_spiral",
    datetime_str="2023-03-03T12:00:00:Z",
    description="RAPID ARRAY simulation",
    glider_model="DEEP",
    inital_heading=225,
    lat_ini=27.225,
    lon_ini=-15.4225,
    glider_name="comet",
    mission_directory="RAPID-mooring_spiral",
    dive_depth=1000,
    spiral=True
)

virtual_mooring_spiral.run_mission()
virtual_mooring_spiral.save_mission()

# waypoints = GliderMissionBuilder.follow_waypoints(
#     mission_name="waypoints2",
#     datetime_str="2023-03-03T12:00:00:Z",
#     description="follow waypoints simulation",
#     glider_model="DEEP",
#     inital_heading=225,
#     lat_ini=27.225,
#     lon_ini=-15.4225,
#     lat_wp=[27.425,27.825],
#     lon_wp=[-15.4225,-15.4225],
#     glider_name="comet",
#     mission_directory="waypoints2",
#     dive_depth=1000
# )

# waypoints.run_mission()
# waypoints.save_mission()