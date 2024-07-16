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
class Extent:
    """
    Extent class
    """
    max_lat: float
    max_lng: float
    min_lat: float
    min_lng: float
    start_time: str
    end_time: str
    max_depth: float

    def __init__(self, trajectory: Trajectory, excess_space: int = 0.5, excess_depth: int = 100, ):
        self.max_lat = np.around(np.max(trajectory.latitudes), 2) + excess_space
        self.min_lat = np.around(np.min(trajectory.latitudes), 2) - excess_space
        self.max_lng = np.around(np.max(trajectory.longitudes), 2) + excess_space
        self.min_lng = np.around(np.min(trajectory.longitudes), 2) - excess_space
        self.start_time = np.datetime_as_string(trajectory.datetimes[0] - np.timedelta64(1, 'D'), unit="D")
        self.end_time = np.datetime_as_string(trajectory.datetimes[-1] + np.timedelta64(1, 'D'), unit="D")
        self.max_depth = np.around(np.max(trajectory.depths), 2) + excess_depth


@dataclass
class Cats:
    """
    Catalog class
    """
    cmems_cat: dict

    # TODO add in some kind of update check so that the json file is updated periodically
    def __init__(self, search: str = "GLOBAL", overwrite=False):
        self.cmems_cat = copernicusmarine.describe(contains=[search],include_datasets=True,
                                                   overwrite_metadata_cache=overwrite)


@dataclass
class World(dict):
    catalog: Cats
    extent: Extent
    interpolator: dict
    matched_worlds: dict
    """
    Creates a dict containing data for the world that the glider will fly through

    Parameters:
    - trajectory: Trajectory object containing the glider trajectory

    Returns:
    - dict with xarray datasets filled with data
    """
    def __init__(self, trajectory: Trajectory, reality: Reality):
        self.catalog = Cats()
        self.extent = Extent(trajectory=trajectory)
        self.interpolator = {}
        self.matched_worlds = {}
        self.__find_worlds(reality=reality)
        ds = {}
        for key, value in self.matched_worlds.items():
            store = self.__get_worlds(key=key, value=value)
            # Create the ds using the separate method
            ds[key] = (xr.open_zarr(store=store))
        # Initialize the base class with the created group attributes
        super().__init__(ds)
        self.__build_world()

    def __find_worlds(self, reality: Reality):
        """
        Finds a world that matches the reality required.

        Parameters:
        - reality: Reality object containing the empty reality the world needs to match

        Returns:
        - Python dict with matched dataset ids and variable names
        """
        # for every array in the reality group
        for key in reality.array_keys():
            self.__find_cmems_worlds(key=key)

    def __get_worlds(self, key, value):
        vars2 = []
        # pull out the var names that CMEMS needs NOTE not the same as Mamma Mia uses
        for k2, v2 in value.items():
            vars2.append(v2)
        zarr_f = (f"{key}_{self.extent.max_lng}_{self.extent.min_lng}_{self.extent.max_lat}_{self.extent.min_lat}_"
                  f"{self.extent.max_depth}_{self.extent.start_time}_{self.extent.end_time}.zarr")
        zarr_d = "copernicus-data/"
        if not os.path.isdir(zarr_d + zarr_f):
            copernicusmarine.subset(
                dataset_id=key,
                variables=vars2,
                minimum_longitude=self.extent.min_lng,
                maximum_longitude=self.extent.max_lng,
                minimum_latitude=self.extent.min_lat,
                maximum_latitude=self.extent.max_lat,
                start_datetime=str(self.extent.start_time),
                end_datetime=str(self.extent.end_time),
                minimum_depth=0,
                maximum_depth=self.extent.max_depth,
                output_filename=zarr_f,
                output_directory=zarr_d,
                file_format="zarr",
                force_download=True
            )
        return zarr_d + zarr_f

    def __build_world(self):
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
                for k1, v1, in self.matched_worlds[key].items():
                    # if variable names match (this is to ensure varible names are consistent)
                    if var == v1:
                        self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(self[key][var])

    def __find_cmems_worlds(self, key: str):
        """
        Traverse CMEMS catalog and find products/datasets that match the glider sensors and
        the trajectory spatial and temporal extent.
        """
        # check each product in cmems catalog
        for k1, v1 in self.catalog.cmems_cat.items():
            for i in range(len(v1)):
                # ensure it is a numerical model
                if v1[i]["sources"][0] != "Numerical models":
                    print("warning product is not a numerical model")
                    break
                # check each dataset
                for j in range(len(v1[i]["datasets"])):
                    dataset = v1[i]["datasets"][j]
                    k = None
                    for k in range(len(dataset["versions"][0]["parts"][0]["services"])):
                        if dataset["versions"][0]["parts"][0]["services"][k]["service_format"] == "zarr" and \
                                dataset["versions"][0]["parts"][0]["services"][k]["service_type"][
                                    "service_name"] == "arco-geo-series":
                            break
                    variables = dataset["versions"][0]["parts"][0]["services"][k]["variables"]
                    # check each variable
                    for m in range(len(variables)):
                        if key not in alias:
                            print(f"variable {key} not in alias file")
                        if variables[m]["short_name"] in alias[key]:
                            # if trajectory spatial extent is within variable data
                            if (variables[m]["bbox"][0] < self.extent.min_lng or
                                    variables[m]["bbox"][1] > self.extent.min_lat
                                    or variables[m]["bbox"][2] > self.extent.max_lng or
                                    variables[m]["bbox"][3] > self.extent.min_lat):
                                # find the time coordinate index
                                n = None
                                for n in range(len(variables[m]["coordinates"])):
                                    if variables[m]["coordinates"][n]["coordinates_id"] == "time":
                                        break
                                try:
                                    start = variables[m]["coordinates"][n]["values"][0]
                                    end = variables[m]["coordinates"][n]["values"][-1]
                                    step = variables[m]["coordinates"][n]["values"][1] - \
                                           variables[m]["coordinates"][n]["values"][0]
                                except TypeError:
                                    start = variables[m]["coordinates"][n]["minimum_value"]
                                    end = variables[m]["coordinates"][n]["maximum_value"]
                                    step = variables[m]["coordinates"][n]["step"]
                                start_traj = float((np.datetime64(self.extent.start_time) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                end_traj = float((np.datetime64(self.extent.end_time) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                # check if trajectory temporal extent is within variable data
                                if start_traj > start and end_traj < end:
                                    # make sure data is at least daily
                                    if step <= 86400000:
                                        if dataset["dataset_id"] in self.matched_worlds:
                                            self.matched_worlds[dataset["dataset_id"]][key] = variables[m]["short_name"]
                                        else:
                                            self.matched_worlds[dataset["dataset_id"]] = {
                                                key: variables[m]["short_name"]}
