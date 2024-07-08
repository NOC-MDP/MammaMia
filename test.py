from src.mission import World, Flight, Trajectory, Autosub, Reality, sensors

# make empty suite of sensors to use in AUV
ss = sensors.SensorSuite()

# add required sensors for mission
ss.groups["CTD"] = sensors.CTD()
ss.groups["ADCP"] = sensors.ADCP()
# create auv adding in sensor suite
auv = Autosub(sensorsuite=ss)

# define which model/world to use
world = World(path="model.zarr")

# define trajectory through world
trajectory = Trajectory(num_points=4)

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
    assert flight.trajectory["latitudes"].__len__() == 4


def test_auv():
    assert flight.auv.name == "Autosub"


def test_flight():
    assert flight.id == 1


def test_model():
    assert flight.world.read_only is True


def test_reality():
    assert flight.reality.read_only is not True
