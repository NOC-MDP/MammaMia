import zarr
import numpy as np
from src.mission.auv import AUV


class Reality(zarr.Group):
    def __init__(self, auv: AUV, numpoints, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        for group in auv.sensors.values():
            for sensor in group.sensors.values():
                self.full(name=sensor.name, shape=numpoints, dtype=np.float64, fill_value=np.nan)
                self.attrs["mapped_name"] = sensor.name
