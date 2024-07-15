from src.mission import World, Mission, Trajectory, Slocum, Reality, sensors

# make empty suite of sensors to use in AUV
Sensors = sensors.SensorSuite()

# add required sensors for mission
# as a defined group
Sensors["CTD1"] = sensors.CTD()
Sensors["BIO1"] = sensors.BIO()

glider = Slocum(sensorsuite=Sensors)

trajectory = Trajectory(glider_traj_path="comet-mm1.nc")
# generate a Slocum glider path based on waypoints and Slocum config
#trajectory.plot_trajectory()
# create reality to return (based on model/world and sensor suite and trajectory)
reality = Reality(glider=glider, trajectory=trajectory)

# define which model/world to use
world = World(trajectory=trajectory,reality=reality)

# put it all together into a flight/mission object
mission = Mission(id=1,
                  description="flight of the conchords",
                  world=world,
                  glider=glider,
                  trajectory=trajectory,
                  reality=reality
                  )
# fly the mission to generate the interpolated data
mission.fly()
mission.show_reality()
print("debug point!")


def test_glider():
    assert mission.glider.name == "Slocum"


def test_flight():
    assert mission.id == 1


def test_reality():
    assert mission.reality.read_only is not True
