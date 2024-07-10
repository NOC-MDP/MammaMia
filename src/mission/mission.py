from dataclasses import dataclass, field
import numpy as np
from src.mission import auv, realities,trajectory,world
import plotly.graph_objects as go

@dataclass
class Mission:
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
                      time=np.array(self.trajectory.trajectory["datetimes"],dtype='datetime64'),
                      )
        self.reality.temperature = self.world.interpolator.quadrivariate(flight)

        print("debug!")

    def show_reality(self):

        x = self.trajectory.trajectory["longitudes"][:,]
        y = self.trajectory.trajectory["latitudes"][:,]
        z = self.trajectory.trajectory["depths"][:,]
        temperature= self.reality.temperature
        fig = go.Figure(data=[go.Scatter3d(x=x,y=y,z=z,mode='markers', marker=dict(
                                                                                size=2,
                                                                                color=temperature,                # set color to an array/list of desired values
                                                                                colorscale='Jet',   # choose a colorscale
                                                                                opacity=0.8,
                                                                                colorbar=dict(thickness=40),
                                                                            ))])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(
            title=dict(text="Glider Reality: Temperature", font=dict(size=25), automargin=True, yref='paper'),
        )
        fig.update_layout(scene=dict(
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            zaxis_title='Depth'),)
        fig.show()
