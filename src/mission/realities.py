import zarr
import numpy as np
#from src.mission import SensorSuite


class Reality(zarr.Group):
    def __init__(self, numpoints=1, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        # # Add any additional initialization here
        # match sensors2:
        #     case SensorSuite:
        #         self.full(name="temperature", shape=numpoints, dtype=np.float64, fill_value=np.nan)
        #         self.full(name="salinity", shape=numpoints, dtype=np.float64, fill_value=np.nan)
        #         self.full(name="U component", shape=numpoints, dtype=np.float64, fill_value=np.nan)
        #         self.full(name="V component", shape=numpoints, dtype=np.float64, fill_value=np.nan)
        #     case _:
        #         raise Exception("unknown reality")
