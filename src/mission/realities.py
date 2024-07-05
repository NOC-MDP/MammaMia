import zarr
import numpy as np
from enum import Enum, auto


# different reality types
class Realities(Enum):
    T = auto()
    TS = auto()
    TSUV = auto()


class Reality(zarr.Group):
    def __init__(self, reality: Realities, numpoints=1, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        # Add any additional initialization here
        match reality:
            case Realities.T:
                self.full(name="temperature", shape=numpoints, dtype=np.float64, fill_value=np.nan)
            case Realities.TS:
                self.full(name="salinity", shape=numpoints, dtype=np.float64, fill_value=np.nan)
            case Realities.TSUV:
                self.full(name="temperature", shape=numpoints, dtype=np.float64, fill_value=np.nan)
                self.full(name="salinty", shape=numpoints, dtype=np.float64, fill_value=np.nan)
                self.full(name="U component", shape=numpoints, dtype=np.float64, fill_value=np.nan)
                self.full(name="V component", shape=numpoints, dtype=np.float64, fill_value=np.nan)
            case _:
                raise Exception("unknown reality")
