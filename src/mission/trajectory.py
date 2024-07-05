import zarr
import numpy as np


class Trajectory(zarr.Group):
    def __init__(self, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)
        self.attrs["created"] = str(np.datetime64("1970-01-01"))
        # Add any additional initialization here

    def new_traj(self, num_points: int):
        self.attrs['created'] = str(np.datetime64("now"))
        self.full(name="latitudes", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        self.full(name="longitudes", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        self.full(name="depths", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        self.full(name="datatimes", shape=(num_points,), dtype="M8[ns]", fill_value="1970-01-01T00:00:00")
        return self

    def update_traj(self, lat: float, lng: float, depth: float, idx: int):
        self["latitudes"][idx] = lat
        self["longitudes"][idx] = lng
        self["depths"][idx] = depth
