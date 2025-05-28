from mamma_mia import GliderMissionBuilder

# virtual_mooring = GliderMissionBuilder.virtual_mooring(
#     mission_name="rapid-mooring",
#     datetime_str="2023-03-03T12:00:00:Z",
#     description="RAPID ARRAY simulation",
#     glider_model="DEEP",
#     inital_heading=225,
#     lat_ini=27.225,
#     lon_ini=-15.4225,
#     glider_name="comet",
#     mission_directory="RAPID-mooring",
#     dive_depth=1000
# )
#
# virtual_mooring.run_mission()
# virtual_mooring.save_mission()

waypoints = GliderMissionBuilder.follow_waypoints(
    mission_name="waypoints",
    datetime_str="2023-03-03T12:00:00:Z",
    description="follow waypoints simulation",
    glider_model="DEEP",
    inital_heading=225,
    lat_ini=27.225,
    lon_ini=-15.4225,
    lat_wp=[27.425,27.825],
    lon_wp=[-15.4225,-15.4225],
    glider_name="comet",
    mission_directory="waypoints",
    dive_depth=1000
)

waypoints.run_mission()
waypoints.save_mission()