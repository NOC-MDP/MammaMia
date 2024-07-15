import copernicusmarine
from src.mission.trajectory import Trajectory
from src.mission.realities import Reality
import numpy as np
import os
import xarray as xr
import pyinterp.backends.xarray
from dataclasses import dataclass
from src.mission.worlds import Worlds
import re

@dataclass
class World(dict):
    """
    Creates a dict containing data for the world that the glider will fly through

    Parameters:
    - trajectory: Trajectory object containing the glider trajectory

    Returns:
    - dict with xarray datasets filled with data
    """
    def __init__(self, trajectory: Trajectory, reality:Reality):
        self.interpolator = {}
        matched = self.__find_worlds(reality,trajectory)
        ds = {}
        for key, value in matched.items():
            store = self.__get_worlds(trajectory=trajectory,key=key,value=value)
            # Create the ds using the separate method
            ds[key] = (xr.open_zarr(store=store))
        # Initialize the base class with the created group attributes
        super().__init__(ds)
        self.__build_world(matched)

    def __find_worlds(self,reality:Reality,trajectory:Trajectory):
        """
        Finds a world that matches the reality and trajectory past to it.

        Parameters:
        - trajectory: Trajectory object containing the glider trajectory
        - reality: Reality object containing the empty reality the world needs to match

        Returns:
        - Python dict with matched dataset ids and variable names
        """
        matched = {}
        # for every array in the reality group
        for key in reality.array_keys():
            # check each world
            for world_id, world_data in Worlds.items():
                # if CMEMS dataset
                if world_data["source"] == "CMEMS":
                    # check each world dataset
                    for dataset_id, dataset_data in world_data["datasets"].items():
                        vars = dataset_data["variables"]
                        # if there is a variable that matches the reality array
                        if key in vars:
                            # check extent is within trajectory extents
                            extent = world_data["extent"]["spatial"]
                            if extent[0] < np.min(trajectory.longitudes) and extent[1] > np.max(trajectory.longitudes) and \
                                extent[2] < np.min(trajectory.latitudes) and extent[3] > np.max(trajectory.latitudes):
                                # check that temporal extent is within trajectory extent
                                t_extent = world_data["extent"]["temporal"]
                                # if forecast model then create temporal extent using dataset specification
                                if world_data["forecast"]:
                                    # match any ints pattern
                                    pattern = r'\d+'
                                    # Use the findall method to get all matches of the pattern
                                    past = int(re.findall(pattern, t_extent[0])[0])
                                    future = int(re.findall(pattern, t_extent[1])[0])
                                    start_t = np.datetime_as_string(np.datetime64("now") - np.timedelta64(int(past)*365, 'D'), unit="s")
                                    end_t = np.datetime_as_string(np.datetime64("now") + np.timedelta64(int(future), 'D'), unit="s")
                                else:
                                    start_t = np.datetime_as_string(trajectory.datetimes[0] - np.timedelta64(1, 'D'), unit="s")
                                    end_t = np.datetime_as_string(trajectory.datetimes[-1] + np.timedelta64(1, 'D'), unit="s")
                                # check to see if trajectory extent is within dataset
                                if start_t > t_extent[0] and end_t < t_extent[1]:
                                    # if dataset id exists add to dictionary entry
                                    if dataset_id in matched:
                                        matched[dataset_id][key] = dataset_data["variables"][key]
                                    # or create the dictionary entry
                                    else:
                                        matched[dataset_id] = {key: dataset_data["variables"][key]}
                else:
                    raise Exception("Only CMEMS sources currently supported")

        return matched

    def __get_worlds(self,trajectory:Trajectory,key,value):
        excess_space = 0.5
        # TODO need ideally dynamically set this using bathy as in deep water 100 might not be enough
        excess_depth = 100
        vars=[]
        # pull out the var names that CMEMS needs NOTE not the same as Mamma Mia uses
        for k2,v2 in value.items():
            vars.append(v2)
        max_lat = np.around(np.max(trajectory.latitudes),2) + excess_space
        min_lat = np.around(np.min(trajectory.latitudes),2) - excess_space
        max_lng = np.around(np.max(trajectory.longitudes),2) + excess_space
        min_lng = np.around(np.min(trajectory.longitudes),2) - excess_space
        start_time = np.datetime_as_string(trajectory.datetimes[0] - np.timedelta64(1, 'D'), unit="D")
        end_time = np.datetime_as_string(trajectory.datetimes[-1] + np.timedelta64(1, 'D'), unit="D")
        max_depth = np.around(np.max(trajectory.depths),2) + excess_depth
        zarr_f = f"{key}_{max_lng}_{min_lng}_{max_lat}_{min_lat}_{max_depth}_{start_time}_{end_time}.zarr"
        zarr_d = "copernicus-data/"
        if not os.path.isdir(zarr_d+zarr_f):
            copernicusmarine.subset(
                dataset_id=key,
                variables=vars,
                minimum_longitude=min_lng,
                maximum_longitude=max_lng,
                minimum_latitude=min_lat,
                maximum_latitude=max_lat,
                start_datetime=str(start_time),
                end_datetime=str(end_time),
                minimum_depth=0,
                maximum_depth=max_depth,
                output_filename=zarr_f,
                output_directory=zarr_d,
                file_format="zarr",
                force_download=True
            )
        return zarr_d+zarr_f


    def __build_world(self,matched):
        """
        Creates a 4D interpolator that allows a world to be interpolated on to a trajectory

        Parameters:
        - None

        Returns:
        - World object with an interpolator
        """
        # for every dataset
        for key in self.keys():
            # for every variable
            for var in self[key]:
                # for each item in matched dictionary
                for k1, v1, in matched[key].items():
                    # if variable names match (this is to ensure varible names are consistent)
                    if var == v1:
                        self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(self[key][var])
