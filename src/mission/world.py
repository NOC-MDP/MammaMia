import copernicusmarine
from src.mission.trajectory import Trajectory
import numpy as np
import os
import xarray as xr
import pyinterp.backends.xarray
from dataclasses import dataclass,field

@dataclass
class World():
    world: xr.Dataset = field(init=False)
    interpolator: pyinterp.backends.xarray.Grid4D = field(init=False)

    def __init__(self, trajectory: Trajectory):
        max_lat = np.max(trajectory.trajectory["latitudes"])
        min_lat = np.min(trajectory.trajectory["latitudes"])
        max_lng = np.max(trajectory.trajectory["longitudes"])
        min_lng = np.min(trajectory.trajectory["longitudes"])
        start_time = np.datetime_as_string(trajectory.trajectory["datatimes"][0]-np.timedelta64(1,'D'), unit="s")
        end_time = np.datetime_as_string(trajectory.trajectory["datatimes"][-1]+np.timedelta64(1,'D'), unit="s")
        max_depth = np.max(trajectory.trajectory["depths"])
        if not os.path.isdir("copernicus-data/CMEMS_world.zarr"):
            copernicusmarine.subset(
                dataset_id="cmems_mod_glo_phy-thetao_anfc_0.083deg_PT6H-i",
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
        self.world = xr.open_zarr(store="copernicus-data/CMEMS_world.zarr")

    def build_interpolator(self):
        self.interpolator = pyinterp.backends.xarray.Grid4D(self.world.thetao)
