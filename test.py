from datetime import datetime
from src.mission import World, Mission, Trajectory, Slocum, Reality, sensors, AUV

# make empty suite of sensors to use in AUV
Sensors = sensors.SensorSuite()

# add required sensors for mission
# as a defined group
Sensors["CTD"] = sensors.CTD()
Sensors["ADCP"] = sensors.ADCP()

# or custom group with a custom sensor
ss2 = sensors.SensorSuite()
ss2["custom group"] = sensors.SensorGroup(
    name="my group",
    sensors={"my sensor": sensors.Sensor(name="my sensor", units="my units")}
)

# build a defined auv while adding in sensor suite
auv = Slocum(sensorsuite=Sensors)
# or make your own!
auv_custom = AUV(name="my AUV",
                 dive_rate=0.1,
                 dive_angle=20,
                 sensors=ss2,
                 surface_rate=0.1,
                 surface_angle=30,
                 target_depth=150,
                 min_depth=10.0,
                 speed=0.5,
                 time_at_depth=10,
                 time_step=60,
                 time_at_surface=10)

# create trajectory object filled with waypoints
trajectory = Trajectory(waypoint_path="waypoints.geojson")
# generate a Slocum glider path based on waypoints and Slocum config
trajectory.create_trajectory(start_time="2023-01-01T00:00:00Z", auv=auv)
trajectory.plot_trajectory()
# create reality to return (based on model/world and sensor suite and trajectory)
reality = Reality(auv=auv,trajectory=trajectory)

# define which model/world to use
world = World(trajectory=trajectory)
world.build_interpolator()

# put it all together into a flight/mission object
mission = Mission(id=1,
                description="flight of the conchords",
                world=world,
                auv=auv,
                trajectory=trajectory,
                reality=reality
                )
# fly the mission to generate the interpolated data
mission.fly()
mission.show_reality()
print("debug point!")


def test_trajectory():
    assert mission.trajectory.waypoints["latitudes"].__len__() == 33


def test_auv():
    assert mission.auv.name == "Slocum"


def test_flight():
    assert mission.id == 1


def test_reality():
    assert mission.reality.read_only is not True

