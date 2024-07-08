import numpy as np

from src.mission import World, Flight, Trajectory, Slocum, Reality, sensors

# make empty suite of sensors to use in AUV
ss = sensors.SensorSuite()

# add required sensors for mission
# as a defined group
ss["CTD"] = sensors.CTD()
ss["ADCP"] = sensors.ADCP()
# or custom group
ss["mygroup"] = sensors.SensorGroup(
                                    name="my group",
                                    sensors={"my sensor": sensors.Sensor(name="my sensor",units="my units")}
                                    )

# build an auv while adding in sensor suite
auv = Slocum(sensorsuite=ss)

# define which model/world to use
world = World(path="model.zarr")

# define trajectory through world
trajectory = Trajectory(waypoint_path="waypoints.geojson")

trajectory.create_trajectory(start_time=np.datetime64("2023-01-01T00:00:00Z"))

# create reality to return (based on model/world and sensor suite and trajectory)
reality = Reality(auv=auv,numpoints=4)

flight = Flight(id=1,
                description="flight of the conchords",
                world=world,
                auv=auv,
                trajectory=trajectory,
                reality=reality
                )
print("debug point!")


def test_trajectory():
    assert flight.trajectory.waypoints["latitudes"].__len__() == 33


def test_auv():
    assert flight.auv.name == "Slocum"


def test_flight():
    assert flight.id == 1


def test_model():
    assert flight.world.read_only is True


def test_reality():
    assert flight.reality.read_only is not True
