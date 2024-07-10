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
        self.attrs["created"] = str(np.datetime64("now"))

        self.glider_ds = xr.open_dataset(glider_traj_path)


    def create_trajectory(self):
        """
        Create a trajectory based on the AUV class using the provided waypoints and AUV specification
        :return:
        """
        num_points = self.glider_ds["LATITUDE"].__len__()
        trajectory = self.create_group(name="trajectory")

        trajectory.full(name="latitudes", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="longitudes", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="depths", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="datetimes", shape=(num_points,), dtype="M8[ns]", fill_value="1970-01-01T00:00:00")

        trajectory["latitudes"] = np.array(self.glider_ds["LATITUDE"])
        trajectory["longitudes"] = np.array(self.glider_ds["LONGITUDE"])
        trajectory["depths"] = np.array(self.glider_ds["GLIDER_DEPTH"])
        trajectory["datetimes"] = np.array(self.glider_ds["TIME"], dtype='datetime64')

    def plot_trajectory(self):

        x = self.trajectory["longitudes"][:,]
        y = self.trajectory["latitudes"][:,]
        z = self.trajectory["depths"][:,]
        dt = np.array(self.trajectory["datetimes"][:,]).tolist()
        fig = go.Figure(data=[go.Scatter3d(x=x,y=y,z=z,mode='markers', marker=dict(
                                                                                size=2,
                                                                                color=dt,                # set color to an array/list of desired values
                                                                                colorscale='Viridis',   # choose a colorscale
                                                                                opacity=0.8,
                                                                                colorbar=dict(thickness=40),
                                                                            ))])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(
            title=dict(text="Glider Trajectory", font=dict(size=25), automargin=True, yref='paper')
        )
        fig.update_layout(scene=dict(
            xaxis_title='Longitude',
            yaxis_title='Latitude',
            zaxis_title='Depth'),)
        fig.show()
