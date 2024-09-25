import uuid
from dataclasses import dataclass,field
import numpy as np
import plotly.graph_objects as go
from loguru import logger
import mamma_mia as mm



@dataclass
class Mission:
    """
    Creates a mamma_mia object

    Parameters:
    - id
    - description
    - world
    - trajectory
    - glider
    -reality

    Returns:
    - Mission object that is ready for flight!
    """
    name: str
    description: str
    id: uuid.UUID = uuid.uuid4()
    world: mm.World = field(init=False)
    trajectory: mm.Trajectory = field(init=False)
    auv: mm.AUV = field(init=False)
    reality: mm.Reality = field(init=False)

    def add_trajectory(self, in_trajectory: mm.Trajectory) -> ():
        self.trajectory = in_trajectory

    def add_world(self, in_world: mm.World) -> ():
        self.world = in_world

    def add_auv(self, in_auv: mm.AUV) -> ():
        self.auv = in_auv

    def add_reality(self, in_reality: mm.Reality) -> ():
        self.reality = in_reality

    def populate_mission(self,auv:mm.AUV,traj_path:str) -> ():
        self.add_auv(in_auv=auv)
        self.add_trajectory(in_trajectory= mm.Trajectory(glider_traj_path=traj_path))
        self.add_reality(in_reality=mm.Reality(auv=self.auv, trajectory=self.trajectory))
        self.add_world(in_world=mm.World(trajectory=self.trajectory,reality=self.reality))

    def fly(self):
        flight = {
            "longitude": np.array(self.trajectory.longitudes),
            "latitude": np.array(self.trajectory.latitudes),
            "depth": np.array(self.trajectory.depths),
            "time": np.array(self.trajectory.datetimes, dtype='datetime64'),
        }
        for key in self.reality.array_keys():
            try:
                self.reality[key] = self.world.interpolator[key].quadrivariate(flight)
            except KeyError:
                logger.warning(f"no interpolator found for parameter {key}")
    def show_reality(self, parameter:str,colourscale:str="Jet"):

        marker = {
            "size": 2,
            "color": self.reality[parameter],
            "colorscale": colourscale,
            "opacity": 0.8,
            "colorbar": {"thickness": 40}
        }
        title = {
            "text": f"Glider Reality: {parameter}",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper"
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }
        fig = go.Figure(data=[
            go.Scatter3d(x=self.trajectory.longitudes, y=self.trajectory.latitudes, z=self.trajectory.depths,mode='markers', marker=marker),
            # TODO implement bathy surface plot
            #go.Surface()
        ])

        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()


