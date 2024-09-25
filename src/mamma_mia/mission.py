from dataclasses import dataclass
import numpy as np
from distlib.util import parse_marker

from mamma_mia import realities, trajectory, world, auv
import plotly.graph_objects as go
from loguru import logger


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
    id: int
    description: str
    world: world.World
    trajectory: trajectory.Trajectory
    auv: auv.AUV
    reality: realities.Reality

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


