import copernicusmarine
from src.mission.trajectory import Trajectory
from src.mission.realities import Reality
import numpy as np
import os
import xarray as xr
import pyinterp.backends.xarray
from dataclasses import dataclass
from src.mission.alias import alias
import copernicusmarine
import json

@dataclass
class Cats:
    cmems_cat: dict

    def __init__(self,overwrite=False):
        if overwrite:
            self.__get_cmems_cat(overwrite=True)
        else:
            try:
                with open("CMEMS_cat.json") as f:
                    self.cmems_cat = json.load(f)
            except FileNotFoundError:
                self.__get_cmems_cat()

    def __get_cmems_cat(self,overwrite=False):
        if overwrite:
            catalog = copernicusmarine.describe(contains=["GLOBAL"],
                                                include_datasets=True,overwrite_metadata_cache=True)
        else:
            catalog = copernicusmarine.describe(contains=["GLOBAL"],
                                                include_datasets=True)
        self.cmems_cat = catalog
        with open("CMEMS_cat.json",'w') as f:
            json.dump(catalog, f)

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
        self.catalog = Cats()
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
            # check each product in catalog
            for k1, v1 in self.catalog.cmems_cat.items():
                for i in range(len(v1)):
                    # ensure its a numerical model
                    if v1[i]["sources"][0] != "Numerical models":
                        print("warning product is not a numerical model")
                        break
                    # check each dataset
                    for j in range(len(v1[i]["datasets"])):
                        dataset = v1[i]["datasets"][j]
                        for k in range(len(dataset["versions"][0]["parts"][0]["services"])):
                            if dataset["versions"][0]["parts"][0]["services"][k]["service_format"] == "zarr" and dataset["versions"][0]["parts"][0]["services"][k]["service_type"]["service_name"] == "arco-geo-series":
                                break
                        variables = dataset["versions"][0]["parts"][0]["services"][k]["variables"]
                        # check each variable
                        for m in range(len(variables)):
                            if key not in alias:
                                print(f"variable {key} not in alias file")
                            if variables[m]["short_name"] in alias[key]:
                                # if trajectory spatial extent is within variable data
                                if variables[m]["bbox"][0] < np.min(trajectory.longitudes) or variables[m]["bbox"][1] > np.min(trajectory.latitudes) \
                                        or variables[m]["bbox"][2] > np.max(trajectory.longitudes) or variables[m]["bbox"][3] > np.max(trajectory.latitudes):
                                    # find the time coordinate index
                                    for n in range(len(variables[m]["coordinates"])):
                                        if variables[m]["coordinates"][n]["coordinates_id"] == "time":
                                            break
                                    try:
                                        start = variables[m]["coordinates"][n]["values"][0]
                                        end = variables[m]["coordinates"][n]["values"][-1]
                                        step = variables[m]["coordinates"][n]["values"][1] - variables[m]["coordinates"][n]["values"][0]
                                    except TypeError:
                                        start = variables[m]["coordinates"][n]["minimum_value"]
                                        end = variables[m]["coordinates"][n]["maximum_value"]
                                        step = variables[m]["coordinates"][n]["step"]
                                    start_traj = float((trajectory.datetimes[0] - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                    end_traj = float((trajectory.datetimes[-1] - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                    # check if trajectory temporal extent is within variable data
                                    if start_traj > start and end_traj < end:
                                        # make sure data is at least daily
                                        if step <= 86400000:
                                            if dataset["dataset_id"] in matched:
                                                matched[dataset["dataset_id"]][key] = variables[m]["short_name"]
                                            else:
                                                matched[dataset["dataset_id"]] = {key: variables[m]["short_name"]}

        return matched

    def __get_worlds(self,trajectory:Trajectory,key,value):
        excess_space = 0.5
        # TODO need ideally dynamically set this using bathy as in deep water 100 might not be enough?
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
