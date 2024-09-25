from mamma_mia import Mission, Slocum, sensors, Campaign, SensorSuite,Trajectory,Reality,World
import zarr


# make empty suite of sensors to use in AUV
Sensors = SensorSuite()

# add required sensors for mamma_mia
# as a defined array
Sensors["CTD1"] = sensors.CTD()
Sensors["BIO1"] = sensors.BIO()

slocum = Slocum(id="Slocum_1",
                sensorsuite=Sensors,
                )
store = zarr.DirectoryStore('slocum-trajectory.zarr')
trajectory = Trajectory(glider_traj_path="comet-mm1.nc")#,store=store)
# generate a Slocum glider path based on waypoints and Slocum config
trajectory.plot_trajectory()
# create reality to return (based on model/world and sensor suite and trajectory)
store2 = zarr.DirectoryStore('mamma-mia.zarr')
reality = Reality(auv=slocum, trajectory=trajectory)#,store=store2)

# define which model/world to use
world = World(trajectory=trajectory,reality=reality)

# put it all together into a flight/mamma_mia object
mission = Mission(name= "mission_1", description="flight of the conchords")
mission.trajectory.plot_trajectory()
mission.add_reality(in_reality=reality)
mission.add_trajectory(in_trajectory=trajectory)
mission.add_world(in_world=world)
mission.add_auv(in_auv=slocum)

campaign = Campaign(name="example campaign",
                    description="single slocum glider flight in the North Sea"
                    )
campaign.add_mission(mission=mission)
# fly the mamma_mia to generate the interpolated data
campaign.run()
# visualise the results
# colourmap options is here https://plotly.com/python/builtin-colorscales/
campaign.missions["mission_1"].show_reality(parameter="temperature")
campaign.missions["mission_1"].show_reality(parameter="salinity",colourscale="haline")
campaign.missions["mission_1"].show_reality(parameter="phosphate",colourscale="algae")

def test_glider():
    assert mission.auv.type == "Slocum"


def test_flight():
    assert mission.id == 1


def test_reality():
    assert mission.reality.read_only is not True
