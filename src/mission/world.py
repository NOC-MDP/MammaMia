import copernicusmarine
from src.mission.trajectory import Trajectory
import numpy as np
import os
import xarray as xr
import pyinterp.backends.xarray
from dataclasses import dataclass

@dataclass
class World(xr.Dataset):
    def __init__(self, trajectory: Trajectory, overwrite=False):
        self.interpolator = None
        max_lat = np.max(trajectory.latitudes)
        min_lat = np.min(trajectory.latitudes)
        max_lng = np.max(trajectory.longitudes)
        min_lng = np.min(trajectory.longitudes)
        start_time = np.datetime_as_string(trajectory.datetimes[0]-np.timedelta64(1,'D'), unit="s")
        end_time = np.datetime_as_string(trajectory.datetimes[-1]+np.timedelta64(1,'D'), unit="s")
        max_depth = np.max(trajectory.depths)
        if not os.path.isdir("copernicus-data/CMEMS_world.zarr"):
            copernicusmarine.subset(
                dataset_id="cmems_mod_glo_phy_my_0.083deg_P1D-m",
                variables=["thetao"],
                minimum_longitude=min_lng-0.5,
                maximum_longitude=max_lng+0.5,
                minimum_latitude=min_lat-0.5,
                maximum_latitude=max_lat+0.5,
                start_datetime=str(start_time),
                end_datetime=str(end_time),
                minimum_depth=0,
                maximum_depth=max_depth+100,
                output_filename="CMEMS_world.zarr",
                output_directory="copernicus-data",
                file_format="zarr",
                force_download=True
            )
        # Create the ds using the separate method
        ds = xr.open_zarr(store="copernicus-data/CMEMS_world.zarr")
        # Initialize the base class with the created group attributes
        super().__init__(ds)

    def build_interpolator(self):
        self.interpolator = pyinterp.backends.xarray.Grid4D(self.thetao)
