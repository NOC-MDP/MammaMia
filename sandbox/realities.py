import zarr
import numpy as np
from sandbox.auv import AUV
from sandbox.trajectory import Trajectory
from dataclasses import dataclass


@dataclass
class Reality(zarr.Group):
    """
    Creates an empty glider reality derived from a zarr group that can be filled with interpolated data from the world object

    Parameters:
    - glider: Glider class object loaded with sensor suite
    - trajectory: Trajectory object loaded from glider simulator
    - store: default None (optional) specify what type of zarr store to use
    - overwrite default False (optional) specify if you want to overwrite an existing zarr store

    Returns:
    - Reality zarr group that is initialized to fit the requried trajectory and sensor suite of glider
    """
    def __init__(self, auv: AUV, trajectory: Trajectory, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        for group in auv.sensor_suite.values():
            for sensor in group.sensors.values():
                self.full(name=sensor.type, shape=trajectory.latitudes.__len__(), dtype=np.float64, fill_value=np.nan)
                self.attrs["mapped_name"] = sensor.type
