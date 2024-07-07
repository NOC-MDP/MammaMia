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
    auv: auv.AUVs
    reality: realities.Reality

    def __post_init__(self):
        self.attributes = {"created": np.datetime64("now")}



