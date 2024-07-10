import zarr
import numpy as np
import plotly.graph_objects as go
import xarray as xr
class Trajectory(zarr.Group):
    """
    pass in a waypoints file or object to build a trajectory
    """

    def __init__(self, glider_traj_path: str, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)
        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        ds = xr.open_dataset(glider_traj_path)

        self.latitudes = np.array(ds["LATITUDE"])
        self.longitudes = np.array(ds["LONGITUDE"])
        self.depths = np.array(ds["GLIDER_DEPTH"])
        self.datetimes = np.array(ds["TIME"], dtype='datetime64')

    def plot_trajectory(self):
        fig = go.Figure(data=[go.Scatter3d(x=self.longitudes,
                                           y=self.latitudes,
                                           z=self.depths,
                                           mode='markers',
                                           marker=dict(
                                                       size=2,
                                                       color=np.array(self.datetimes).tolist(),
                                                       colorscale='Viridis',
                                                       opacity=0.8,
                                                       colorbar=dict(thickness=40),
                                                      )
                                           )])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(
            title=dict(text="Glider Trajectory",
                       font=dict(size=25),
                       automargin=True,
                       yref='paper')
        )
        fig.update_layout(scene=dict(
                                    xaxis_title='Longitude',
                                    yaxis_title='Latitude',
                                    zaxis_title='Depth'),
                                    )
        fig.show()
