import zarr
import numpy as np
import plotly.graph_objects as go
import xarray as xr
from dataclasses import dataclass


@dataclass
class Trajectory(zarr.Group):
    """
    Creates a Trajectory object (extended zarr group) from an xarray Dataset.

    Parameters:
    - glider_traj_path: string representing glider dataset
    - store: zarr store to store zarr Group (optional) by default a memory store is used
    - overwrite: bool representing whether to overwrite existing zarr Group

    Returns:
    - Trajectory object derived from zarr group
    """

    def __init__(self, glider_traj_path: str, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)
        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        ds = xr.open_dataset(glider_traj_path)

        self.latitudes = np.array(ds["m_lat"])
        self.longitudes = np.array(ds["m_lon"])
        self.depths = np.array(ds["m_depth"])
        self.datetimes = np.array(ds["time"], dtype='datetime64')

        for i in range(self.longitudes.__len__()):
            self.longitudes[i] = self.__convertToDecimal(self.longitudes[i])
        for i in range(self.latitudes.__len__()):
            self.latitudes[i] = self.__convertToDecimal(self.latitudes[i])

    def plot_trajectory(self):
        """
        Creates a plotly figure of the Trajectory object.

        Parameters:
        None

        Returns:
        - Plotly figure of the Trajectory object. (This will open in a web browser)
        """
        marker = {
            "size": 2,
            "color": np.array(self.datetimes).tolist(),
            "colorscale": "Viridis",
            "opacity": 0.8,
            "colorbar": {"thickness": 40}
        }

        title = {
            "text": "Glider Trajectory",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper"
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }

        fig = go.Figure(
            data=[go.Scatter3d(x=self.longitudes, y=self.latitudes, z=self.depths, mode='markers', marker=marker)])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()

    # From: https://github.com/smerckel/latlon/blob/main/latlon/latlon.py
    # Lucas Merckelbach
    def __convertToDecimal(self,x):
        ''' Converts a latitiude or longitude in NMEA format to decimale degrees'''
        sign=np.sign(x)
        xAbs=np.abs(x)
        degrees=np.floor(xAbs/100.)
        minutes=xAbs-degrees*100
        decimalFormat=degrees+minutes/60.
        return decimalFormat*sign