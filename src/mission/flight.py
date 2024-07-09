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
        flight = dict(longitude=np.array(self.trajectory.trajectory["latitudes"]),
                      latitude=np.array(self.trajectory.trajectory["longitudes"]),
                      depth=np.array(self.trajectory.trajectory["depths"]),
                      time=np.array(self.trajectory.trajectory["datatimes"],dtype='datetime64'),
                      )

        # lng = np.empty(shape=1)
        # lng[0] = 43.0
        # lat = np.empty(shape=1)
        # lat[0] = -15
        # depth = np.empty(shape=1)
        # depth[0] = 5
        # time = np.array(["2023-01-01T12:15:00"], dtype='datetime64')
        #
        # A = self.interpolator.quadrivariate(dict(longitude=lng,
        #                                          latitude=lat,
        #                                          depth=depth,
        #                                          time=time,
        #                                          ))

        self.reality.temperature = self.world.interpolator.quadrivariate(flight)




