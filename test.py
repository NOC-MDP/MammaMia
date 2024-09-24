from mamma_mia import World, Mission, Trajectory, Slocum, Reality, sensors, Campaign
import zarr


# make empty suite of sensors to use in AUV
Sensors = sensors.SensorSuite()

# add required sensors for mamma_mia
# as a defined group
Sensors["CTD1"] = sensors.CTD()
Sensors["BIO1"] = sensors.BIO()

slocum = Slocum(sensorsuite=Sensors, id="Slocum_1")
#store = zarr.DirectoryStore('slocum-trajectory.zarr')
trajectory = Trajectory(glider_traj_path="comet-mm1.nc")#,store=store)
# generate a Slocum glider path based on waypoints and Slocum config
trajectory.plot_trajectory()
# create reality to return (based on model/world and sensor suite and trajectory)
#store2 = zarr.DirectoryStore('mamma-mia.zarr')
reality = Reality(auv=slocum, trajectory=trajectory)#,store=store2)

# define which model/world to use
world = World(trajectory=trajectory,reality=reality)

# put it all together into a flight/mamma_mia object
mission = Mission(id=1,
                  description="flight of the conchords",
                  world=world,
                  auv=slocum,
                  trajectory=trajectory,
                  reality=reality
                  )

campaign = Campaign(name="example campaign",
                    description="single slocum glider flight in the North Sea",
                    missions= {"mission_1": mission}
                    )
# fly the mamma_mia to generate the interpolated data
campaign.missions["mission_1"].fly()
# visualise the results
# colourmap options is here https://plotly.com/python/builtin-colorscales/
campaign.missions["mission_1"].show_reality(parameter="temperature")
campaign.missions["mission_1"].show_reality(parameter="salinity",colourscale="haline")
campaign.missions["mission_1"].show_reality(parameter="phosphate",colourscale="algae")

def test_glider():
    assert mission.auv.name == "Slocum"


def test_flight():
    assert mission.id == 1


def test_reality():
    assert mission.reality.read_only is not True
