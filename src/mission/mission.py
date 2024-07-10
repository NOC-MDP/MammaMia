from dataclasses import dataclass
import numpy as np
from src.mission import auv, realities, trajectory, world
import plotly.graph_objects as go


@dataclass
class Mission:
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
        self.reality.temperature = self.world.interpolator.quadrivariate(flight)

    def show_reality(self):
        marker = {
            "size": 2,
            "color": self.reality.temperature,
            "colorscale": "Jet",
            "opacity": 0.8,
            "colorbar": {"thickness": 40}
        }
        title = {
            "text": "Glider Reality: Temperature",
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
            go.Scatter3d(x=self.trajectory.longitudes, y=self.trajectory.latitudes, z=self.trajectory.depths,
                         mode='markers', marker=marker)])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()
