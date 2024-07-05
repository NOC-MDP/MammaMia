from src.mission import Realities, Reality, Model, Flight, Trajectory, Autosub

flight = Flight(id=1,
                description="flight of the conchords",
                model=Model(path="model.zarr"),
                auv=Autosub(name="AL3"),
                trajectory=Trajectory(num_points=4),
                reality=Reality(reality=Realities.TSUV)
                )


def test_trajectory():
    assert flight.trajectory["latitudes"].__len__() == 4


def test_auv():
    assert flight.auv.name == "Autosub AL3"


def test_flight():
    assert flight.id == 1


def test_model():
    assert flight.model.read_only is True


def test_reality():
    assert flight.reality.read_only is not True
