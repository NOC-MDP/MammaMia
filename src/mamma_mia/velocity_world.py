from dataclasses import dataclass
import zarr
import uuid
import numpy as np

@dataclass
class VelocityWorld(zarr.Group):

    def __init__(self,
                 extent: dict,
                 store=None,
                 overwrite=False,
                 excess_space: float = 0.5,
                 excess_depth: int = 100,
                 msm_priority: int = 2,
                 cmems_priority: int = 1,

                 ):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        self.attrs["name"] = "velocity_world"
        self.attrs["uuid"] = str(uuid.uuid4())
        self.attrs["description"] = "world to get interpolated velocities"

        worlds = self.create_group("world")
        extent_excess = {
            "max_lat": extent["max_lat"] + excess_space,
            "min_lat": extent["min_lat"] - excess_space,
            "max_lng": extent["max_lng"] + excess_space,
            "min_lng": extent["min_lng"] - excess_space,
            # TODO dynamically set the +/- delta on start and end time based on time step of model (need at least two time steps)
            "start_time": np.datetime_as_string(extent["start_time"] - np.timedelta64(30, 'D'), unit="D"),
            "end_time": np.datetime_as_string(extent["end_time"] + np.timedelta64(30, 'D'), unit="D"),
            "max_depth": extent["max_depth"] + excess_depth
        }
        worlds.attrs["extent"] = extent_excess
        worlds.attrs["catalog_priorities"] = {"msm": msm_priority, "cmems": cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}

        # create cats
        # find worlds
        # get worlds
        # build interpolator
        # create interface/vector call