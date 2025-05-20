from mamma_mia import MissionBuilder

sim = MissionBuilder.create_mission(
    mission_name="rapid-mooring",
    datetime_str="2023-03-03T12:00:00:Z",
    description="RAPID ARRAY simulation",
    glider_model="DEEP",
    inital_heading=225,
    lat_ini=27.225,
    lon_ini=-15.4225,
    glider_name="comet",
    mission_directory="RAPID-mooring",
)
sim.loadmission(verbose=True)
sim.run(dt=0.5,CPUcycle=4,maxSimulationTime=1, end_on_surfacing=False, end_on_grounding=False,verbose=True)
sim.save()