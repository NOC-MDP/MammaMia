from src.mission import World, Flight, Trajectory, Autosub, Reality, sensors

# make empty suite of sensors to use in AUV
ss = sensors.SensorSuite()

# add required sensors for mission
ss["sensor1"] = sensors.CTD(name="CTD1")
ss["sensor2"] = sensors.ADCP(name="ADCP1")

# create auv adding in sensor suite
auv = Autosub(sensorsuite=ss)

# define which model/world to use
world = World(path="model.zarr")

# define trajectory through world
trajectory = Trajectory(num_points=4)

# create reality to return (based on model/world and sensor suite and trajectory)
reality = Reality()

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
    assert flight.model.read_only is True


def test_reality():
    assert flight.reality.read_only is not True
