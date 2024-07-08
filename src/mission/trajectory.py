import zarr
import numpy as np
import geojson


class Trajectory(zarr.Group):
    """
    pass in a waypoints file or object to build a trajectory
    """
    def __init__(self, waypoint_path: str, store=None, overwrite=False):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)
        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)
        self.attrs["created"] = str(np.datetime64("now"))

        with open(waypoint_path, "r") as f:
            gj = geojson.load(f)
        features = gj["features"]

        waypts = self.create_group(name="waypoints")
        # Add any additional initialization here
        waypts.attrs['created'] = str(np.datetime64("now"))
        waypts.full(name="latitudes", shape=(features.__len__(),), dtype=np.float64, fill_value=np.nan)
        waypts.full(name="longitudes", shape=(features.__len__(),), dtype=np.float64, fill_value=np.nan)
        waypts.full(name="depths", shape=(features.__len__(),), dtype=np.float64, fill_value=np.nan)
        waypts.full(name="datatimes", shape=(features.__len__(),), dtype="M8[ns]", fill_value="1970-01-01T00:00:00")

        for i in range(features.__len__()):
            waypts["longitudes"][i] = features[i].geometry.coordinates[0][0]
            waypts["latitudes"][i] = features[i].geometry.coordinates[0][1]

        trajectory = self.create_group(name="trajectory")
        trajectory.full(name="latitudes", shape=(features.__len__(),), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="longitudes", shape=(features.__len__(),), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="depths", shape=(features.__len__(),), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="datatimes", shape=(features.__len__(),), dtype="M8[ns]", fill_value="1970-01-01T00:00:00")

    def create_trajectory(self):
        """
        Create a trajectory based on the AUV class using the provided waypoints.
        :return:
        """
        pass

    def update_traj(self, lat: float, lng: float, depth: float, idx: int):
        self["latitudes"][idx] = lat
        self["longitudes"][idx] = lng
        self["depths"][idx] = depth
