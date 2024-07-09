from dataclasses import dataclass, field
import numpy as np
from src.mission import auv, realities,trajectory,world


@dataclass
class Flight:
    id: int
    attributes: dict = field(init=False)
    description: str
    world: world.World
    trajectory: trajectory.Trajectory
    auv: auv.AUV
    reality: realities.Reality

    def __post_init__(self):
        self.attributes = {"created": np.datetime64("now")}

    def fly(self):
        flight = dict(longitude=np.array(self.trajectory.trajectory["longitudes"]),
                      latitude=np.array(self.trajectory.trajectory["latitudes"]),
                      depth=np.array(self.trajectory.trajectory["depths"]),
                      time=np.array(self.trajectory.trajectory["datatimes"],dtype='datetime64'),
                      )
        self.reality.temperature = self.world.interpolator.quadrivariate(flight)

        print("debug!")


