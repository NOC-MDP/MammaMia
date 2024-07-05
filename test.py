from src.mission import Model, Flight, Trajectory, Autosub,Reality,sensors


flight = Flight(id=1,
                description="flight of the conchords",
                model=Model(path="model.zarr"),
                auv=Autosub(sensors=sensors.CTD),
                trajectory=Trajectory(num_points=4),
                reality=Reality(sensors2=sensors.CTD)
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
