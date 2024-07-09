import zarr
import numpy as np
import geojson
from math import radians, cos, sin, asin, sqrt
from datetime import timedelta, datetime
from src.mission import auv as auv2


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

    def create_trajectory(self, start_time: datetime, auv: auv2.AUV):
        """
        Create a trajectory based on the AUV class using the provided waypoints and AUV specification
        :return:
        """
        if not isinstance(auv, auv2.AUV):
            raise Exception("auv must be an AUV object")
        min_depth = 0.5
        # TODO clean up this code, e.g. lat_way and lng_way will be accessible via self.
        lats, lngs, depths, times = self.__interpolate_waypoints(lat_way=self.waypoints["latitudes"],
                                                                 lng_way=self.waypoints["longitudes"],
                                                                 start_time=start_time,
                                                                 speed_ms=auv.speed,
                                                                 interval_seconds=auv.time_step,
                                                                 sink_rate=auv.dive_rate,
                                                                 surface_rate=auv.surface_rate,
                                                                 target_depth=auv.target_depth,
                                                                 dive_angle=auv.dive_angle,
                                                                 surface_angle=auv.surface_angle,
                                                                 time_surface=auv.time_surface,
                                                                 time_depth=auv.time_depth,
                                                                 min_depth=min_depth
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

    @staticmethod
    def __haversine(lon1, lat1, lon2, lat2):
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

    def __interpolate_waypoints(self, lat_way, lng_way, start_time, speed_ms, interval_seconds, sink_rate, surface_rate,
                                target_depth, surface_angle, dive_angle, time_surface, time_depth,min_depth):
        # Convert speed to km/s
        speed_kms = speed_ms / 1000.0

        # Convert pitch angle to radians
        dive_radians = radians(dive_angle)
        surface_radians = radians(surface_angle)

        # Adjust sink and surface rates based on pitch angle
        effective_sink_rate = sink_rate * cos(dive_radians)
        effective_surface_rate = surface_rate * cos(surface_radians)

        # Prepare lists for results
        interpolated_lats = []
        interpolated_lngs = []
        interpolated_depths = []
        interpolated_times = []

        # Initialize time
        current_time = start_time
        current_depth = min_depth

        for i in range(len(lat_way) - 1):

            lat1 = lat_way[i]
            lon1 = lng_way[i]
            lat2 = lat_way[i + 1]
            lon2 = lng_way[i + 1]

            # Calculate distance between waypoints
            distance = self.__haversine(lat1, lon1, lat2, lon2)

            # Calculate time to travel this segment
            time_to_travel = distance / speed_kms

            # Calculate time to sink to target depth and back to surface
            time_to_sink = target_depth / effective_sink_rate
            time_to_surface = target_depth / effective_surface_rate

            # Calculate time to travel at target depth
            time_at_depth = interval_seconds * time_depth
            time_at_surface = interval_seconds * time_surface

            # Number of intervals for each phase
            num_intervals_sink = int(time_to_sink // interval_seconds)
            num_intervals_surface = int(time_to_surface // interval_seconds)

            if time_to_travel < time_to_sink + time_to_surface + time_at_depth:
                raise ValueError(
                    "Speed is too slow or target depth is too high to complete the travel within segment time.")

            # Number of intervals for traveling at target depth
            num_intervals_travel = int((time_at_depth) // interval_seconds)

            # Interpolation during sinking
            for j in range(num_intervals_sink + 1):
                t = j / num_intervals_sink if num_intervals_sink > 0 else 1
                interpolated_lat = lat1 + t * (lat2 - lat1) * (time_to_sink / time_to_travel)
                interpolated_lng = lon1 + t * (lon2 - lon1) * (time_to_sink / time_to_travel)
                interpolated_depth = current_depth + t * target_depth

                interpolated_lats.append(interpolated_lat)
                interpolated_lngs.append(interpolated_lng)
                interpolated_depths.append(interpolated_depth)
                interpolated_times.append(current_time)

                current_time += timedelta(seconds=interval_seconds)

            # Interpolation during travel at target depth
            for j in range(num_intervals_travel):
                t = j / 1 if num_intervals_travel > 0 else 1
                interpolated_lat = lat1 + (time_to_sink / time_to_travel) * (lat2 - lat1) + t * (lat2 - lat1) * (
                        time_at_depth / time_to_travel)
                interpolated_lng = lon1 + (time_to_sink / time_to_travel) * (lon2 - lon1) + t * (lon2 - lon1) * (
                        time_at_depth / time_to_travel)
                interpolated_depth = target_depth

                interpolated_lats.append(interpolated_lat)
                interpolated_lngs.append(interpolated_lng)
                interpolated_depths.append(interpolated_depth)
                interpolated_times.append(current_time)

                current_time += timedelta(seconds=interval_seconds)

            # Interpolation during surfacing
            for j in range(num_intervals_surface + 1):
                t = j / num_intervals_surface if num_intervals_surface > 0 else 1
                interpolated_lat = lat1 + ((time_to_sink + time_at_depth) / time_to_travel) * (lat2 - lat1) + t * (
                        lat2 - lat1) * (time_to_surface / time_to_travel)
                interpolated_lng = lon1 + ((time_to_sink + time_at_depth) / time_to_travel) * (lon2 - lon1) + t * (
                        lon2 - lon1) * (time_to_surface / time_to_travel)
                interpolated_depth = target_depth - t * target_depth
                if interpolated_depth < min_depth:
                    interpolated_depth = min_depth

                interpolated_lats.append(interpolated_lat)
                interpolated_lngs.append(interpolated_lng)
                interpolated_depths.append(interpolated_depth)
                interpolated_times.append(current_time)

                current_time += timedelta(seconds=interval_seconds)

            # Interpolation during travel at surface
            for j in range(num_intervals_travel):
                t = j / 1 if num_intervals_travel > 0 else 1
                interpolated_lat = lat1 + (time_to_sink / time_to_travel) * (lat2 - lat1) + t * (lat2 - lat1) * (
                        time_at_surface / time_to_travel)
                interpolated_lng = lon1 + (time_to_sink / time_to_travel) * (lon2 - lon1) + t * (lon2 - lon1) * (
                        time_at_surface / time_to_travel)
                interpolated_depth = min_depth

                interpolated_lats.append(interpolated_lat)
                interpolated_lngs.append(interpolated_lng)
                interpolated_depths.append(interpolated_depth)
                interpolated_times.append(current_time)

                current_time += timedelta(seconds=interval_seconds)

            current_depth = min_depth  # Reset depth to surface at the end of each segment

        # Add the final waypoint at the surface
        interpolated_lats.append(lat2)
        interpolated_lngs.append(lon2)
        interpolated_depths.append(min_depth)
        interpolated_times.append(current_time)

        return interpolated_lats, interpolated_lngs, interpolated_depths, interpolated_times
