from src.mission import Realities, Reality, Model, Flight, Trajectory,Autosub


flight = Flight(id=1,
                description="flight of the concords",
                model=Model(name="test"),
                auv=Autosub(name="AL3"),
                trajectory=Trajectory(),
                reality=Reality(reality=Realities.TSUV)

                )
flight.trajectory.new_traj(num_points=4)
print(flight.trajectory.info)
print(flight.reality.info)
print(flight.trajectory.attrs.asdict())