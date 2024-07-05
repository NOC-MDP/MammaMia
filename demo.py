from src.mission import Realities, Reality, Model, Flight, Trajectory,Autosub
from zarr.storage import DirectoryStore



flight = Flight(id=1,
                description="flight of the concords",
                model=Model(path="model.zarr"),
                auv=Autosub(name="AL3"),
                trajectory=Trajectory(num_points=4),
                reality=Reality(reality=Realities.TSUV)

                )
print(flight.trajectory.info)
print(flight.reality.info)
print(flight.trajectory.attrs.asdict())
flight.model.build_tree()
print(flight.model.info)