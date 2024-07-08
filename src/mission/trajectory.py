import zarr
import numpy as np
import geojson
from math import radians, cos, sin, asin, sqrt
from datetime import timedelta, datetime


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

    def create_trajectory(self, start_time: np.datetime64):
        """
        Create a trajectory based on the AUV class using the provided waypoints and AUV specification
        :return:
        """
        # TODO get AUV parameters from AUV class
        # TODO get interval from sensor class?
        speed = 0.25
        sink_rate = 0.01
        surface_rate = 0.01
        start_depth = 0
        target_depth = 200

        traj_interval = 900
        start_time = datetime(2023, 1, 1)
        lats, lngs, depths, times = interpolate_waypoints(lat_way=self.waypoints["latitudes"],
                                                          lng_way=self.waypoints["longitudes"],
                                                          start_time=start_time,
                                                          speed_ms=speed,
                                                          interval_seconds=traj_interval,
                                                          sink_rate=sink_rate,
                                                          surface_rate=surface_rate,
                                                          start_depth=start_depth,
                                                          target_depth=target_depth
                                                          )
        num_points = lats.__len__()
        trajectory = self.create_group(name="trajectory")
        trajectory.full(name="latitudes", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="longitudes", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="depths", shape=(num_points,), dtype=np.float64, fill_value=np.nan)
        trajectory.full(name="datatimes", shape=(num_points,), dtype="M8[ns]", fill_value="1970-01-01T00:00:00")

        for i in range(num_points):
            trajectory["latitudes"][i] = lats[i]
            trajectory["longitudes"][i] = lngs[i]
            trajectory["depths"][i] = depths[i]
            trajectory["datatimes"][i] = times[i]

    def update_traj(self, lat: float, lng: float, depth: float, idx: int):
        self["latitudes"][idx] = lat
        self["longitudes"][idx] = lng
        self["depths"][idx] = depth


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometres. Use 3956 for miles. Determines return value units.
    return c * r


def interpolate_waypoints(lat_way, lng_way, start_time, speed_ms, interval_seconds, sink_rate, surface_rate,
                          start_depth, target_depth):
    # Convert speed to km/s
    speed_kms = speed_ms / 1000.0

    # Prepare lists for results
    interpolated_lats = []
    interpolated_lngs = []
    interpolated_depths = []
    interpolated_times = []

    # Initialize time
    current_time = start_time
    current_depth = start_depth

    for i in range(len(lat_way) - 1):

        lat1 = lat_way[i]
        lon1 = lng_way[i]
        lat2 = lat_way[i + 1]
        lon2 = lng_way[i + 1]

        # Calculate distance between waypoints
        distance = haversine(lat1, lon1, lat2, lon2)

        # Calculate time to travel this segment
        time_to_travel = distance / speed_kms

        # Calculate time to sink to target depth and back to surface
        time_to_sink = target_depth / sink_rate
        time_to_surface = target_depth / surface_rate

        # Calculate time to travel at target depth
        time_at_depth = interval_seconds

        if time_to_travel < time_to_sink + time_to_surface + time_at_depth:
            raise ValueError(
                "Speed is too slow or target depth is too high to complete the travel within segment time.")

        # Number of intervals for each phase
        num_intervals_sink = int(time_to_sink // interval_seconds)
        num_intervals_travel = int(time_at_depth // interval_seconds)
        num_intervals_surface = int(time_to_surface // interval_seconds)

        # Interpolation during sinking
        for j in range(num_intervals_sink + 1):
            t = j / num_intervals_sink if num_intervals_sink > 0 else 1
            interpolated_lat = lat1 + t * (lat2 - lat1) / 2  # Move halfway while sinking
            interpolated_lng = lon1 + t * (lon2 - lon1) / 2  # Move halfway while sinking
            interpolated_depth = current_depth + t * target_depth

            interpolated_lats.append(interpolated_lat)
            interpolated_lngs.append(interpolated_lng)
            interpolated_depths.append(interpolated_depth)
            interpolated_times.append(current_time)

            current_time += timedelta(seconds=interval_seconds)

        # Interpolation during travel at target depth
        for j in range(num_intervals_travel + 1):
            t = j / num_intervals_travel if num_intervals_travel > 0 else 1
            interpolated_lat = lat1 + 0.5 * (lat2 - lat1) + t * (lat2 - lat1) / 2  # Move remaining halfway
            interpolated_lng = lon1 + 0.5 * (lon2 - lon1) + t * (lon2 - lon1) / 2  # Move remaining halfway
            interpolated_depth = target_depth

            interpolated_lats.append(interpolated_lat)
            interpolated_lngs.append(interpolated_lng)
            interpolated_depths.append(interpolated_depth)
            interpolated_times.append(current_time)

            current_time += timedelta(seconds=interval_seconds)

        # Interpolation during surfacing
        for j in range(num_intervals_surface + 1):
            t = j / num_intervals_surface if num_intervals_surface > 0 else 1
            interpolated_lat = lat1 + t * (lat2 - lat1)  # Move full way while surfacing
            interpolated_lng = lon1 + t * (lon2 - lon1)  # Move full way while surfacing
            interpolated_depth = target_depth - t * target_depth

            interpolated_lats.append(interpolated_lat)
            interpolated_lngs.append(interpolated_lng)
            interpolated_depths.append(interpolated_depth)
            interpolated_times.append(current_time)

            current_time += timedelta(seconds=interval_seconds)

        current_depth = 0  # Reset depth to surface at the end of each segment

    # Add the final waypoint at the surface
    interpolated_lats.append(lat2)
    interpolated_lngs.append(lon2)
    interpolated_depths.append(0)
    interpolated_times.append(current_time)

    return interpolated_lats, interpolated_lngs, interpolated_depths, interpolated_times
