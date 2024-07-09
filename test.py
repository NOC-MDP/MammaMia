from datetime import datetime

from src.mission import World, Flight, Trajectory, Slocum, Reality, sensors, AUV

# make empty suite of sensors to use in AUV
ss = sensors.SensorSuite()

# add required sensors for mission
# as a defined group
ss["CTD"] = sensors.CTD()
ss["ADCP"] = sensors.ADCP()
# or custom group with a custom sensor
ss2 = sensors.SensorSuite()
ss2["custom group"] = sensors.SensorGroup(
    name="my group",
    sensors={"my sensor": sensors.Sensor(name="my sensor", units="my units")}
)

# build a defined auv while adding in sensor suite
auv = Slocum(sensorsuite=ss)
# or make your own!
auv_custom = AUV(name="my AUV",
                 dive_rate=0.1,
                 dive_angle=20,
                 sensors=ss2,
                 surface_rate=0.1,
                 surface_angle=30,
                 target_depth=150,
                 speed=0.5,
                 time_depth=10,
                 time_step=60,
                 time_surface=10)

# create trajectory object filled with waypoints
trajectory = Trajectory(waypoint_path="waypoints.geojson")
# generate a Slocum glider path based on waypoints and Slocum config
trajectory.create_trajectory(start_time=datetime(2023, 1, 1), auv=auv)

# create reality to return (based on model/world and sensor suite and trajectory)
reality = Reality(auv=auv,trajectory=trajectory)

# define which model/world to use
world = World(trajectory=trajectory)
world.build_interpolator()

flight = Flight(id=1,
                description="flight of the conchords",
                world=world,
                auv=auv,
                trajectory=trajectory,
                reality=reality
                )
flight.fly()
print("debug point!")


def test_trajectory():
    assert flight.trajectory.waypoints["latitudes"].__len__() == 33


def test_auv():
    assert flight.auv.name == "Slocum"


def test_flight():
    assert flight.id == 1


def test_reality():
    assert flight.reality.read_only is not True

