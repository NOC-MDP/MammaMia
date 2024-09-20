from mamma_mia.trajectory import Trajectory
from mamma_mia.realities import Reality
import numpy as np
import os
import xarray as xr
import pyinterp.backends.xarray
from dataclasses import dataclass
from mamma_mia.alias import alias
import copernicusmarine
import intake
from datetime import datetime


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
        self.start_time = np.datetime_as_string(trajectory.datetimes[0] - np.timedelta64(14, 'D'), unit="D")
        self.end_time = np.datetime_as_string(trajectory.datetimes[-1] + np.timedelta64(14, 'D'), unit="D")
        self.max_depth = np.around(np.max(trajectory.depths), 2) + excess_depth


@dataclass
class Cats:
    """
    Catalog class
    """
    cmems_cat: dict
    msm_cat: intake.Catalog

    # TODO add in some kind of update check so that the json file is updated periodically
    def __init__(self, search: str = "GLOBAL", overwrite=False,cat_path:str=None):
        self.cmems_cat = copernicusmarine.describe(contains=[search], include_datasets=True,
                                                   overwrite_metadata_cache=overwrite)
        if cat_path is None:
            print("no MSM catalog path provided, can only use CMEMS data")
            self.msm_cat = None
        else:
            try:
                self.msm_cat = intake.open_catalog(cat_path)
            except FileNotFoundError:
                raise Exception("Catalog path {} does not exist".format(cat_path))

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
        # TODO fix the hardcoded cat path so that it checks a path on obj store
        self.catalog = Cats(cat_path="/Users/thopri/MammaMia/src/mamma_mia/catalog.yml")
        self.extent = Extent(trajectory=trajectory)
        self.matched_worlds = {}
        self.__find_worlds(reality=reality)
        ds = {}
        for key, value in self.matched_worlds.items():
            store = self.__get_worlds(key=key, value=value)
            # Create the ds using the separate method
            ds[key] = (xr.open_zarr(store=store))
        # Initialize the base class with the created group attributes
        super().__init__(ds)
        self.interpolator = {}
        self.__build_worlds()

    def __find_worlds(self, reality: Reality):
        """
        Finds a world that matches the reality required.

        Parameters:
        - reality: Reality object containing the empty reality the world needs to match

        Returns:
        - Python dict with matched dataset ids and variable names

        Notes:
        This is a wrapper function around specific find world functions e.g. CMEMS or Jasmin
        """
        # for every array in the reality group
        for key in reality.array_keys():
            self.__find_cmems_worlds(key=key)
            if self.catalog.msm_cat is not None:
                self.__find_msm_worlds(key=key)

    def __get_worlds(self, key, value):
        """
        Gets a matched world from its respective source

        Parameters:
        - key: string that represents the world id
        - value: dictionary of variables to subset from world

        Returns:
        - zarr store: string that denotes where the zarr store holding the world has been saved.

        Notes:
        This is a wrapper function around specific get world functions e.g. CMEMS or Jasmin
        """
        split_key = key.split("_")
        if split_key[0] == "cmems":
            zarr_store = self.__get_cmems_worlds(key=key, value=value)
        elif split_key[0] == "msm":
            zarr_store = self.__get_msm_worlds(key=key, value=value)
        else:
            raise Exception("unknown model source")
        return zarr_store

    def __build_worlds(self):
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
                    # if variable names match (this is to ensure variable names are consistent)
                    if var == v1:
                        split_key = key.split("_")
                        if split_key[0] == "msm":
                            # rename time and depth dimensions to be consistent
                            ds = self[key][var].rename({"deptht": "depth","time_counter": "time"})
                            # Set lat and lon as coordinates replacing x and y
                            ds = ds.assign_coords(latitude=self[key][var]['nav_lat'] , longitude=self[key][var]['nav_lon'] )

                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(ds,geodetic=True)
                        elif split_key[0] == "cmems":
                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(self[key][var],geodetic=True)
                        else:
                            raise Exception("unknown model source")

    def __find_msm_worlds(self, key:str):
        """

        Args:
            key: string that represents the variable to find

        Returns:
            matched worlds dictionary containing dataset ids and variable names

        """
        for k1,v1 in self.catalog.msm_cat.items():
            metadata = v1.describe()['metadata']
            aliases = metadata.get('aliases', [])
            spatial_extent = metadata.get('spatial_extent', [])
            temporal_extent = metadata.get('temporal_extent', [])
            start_traj = float((np.datetime64(self.extent.start_time) - np.datetime64(
                '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
            end_traj = float((np.datetime64(self.extent.end_time) - np.datetime64(
                '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
            if temporal_extent:
                start_datetime = datetime.fromisoformat(temporal_extent[0].replace("Z", "+00:00")).timestamp()*1000
                end_datetime = datetime.fromisoformat(temporal_extent[1].replace("Z", "+00:00")).timestamp()*1000

                # Check if the item is within the desired date range and spatial bounds
                if (spatial_extent and
                        self.extent.min_lat >= spatial_extent[0] and self.extent.max_lat <= spatial_extent[2] and
                        self.extent.min_lng >= spatial_extent[1] and self.extent.max_lng <= spatial_extent[3] and
                        start_traj >= start_datetime and end_traj <= end_datetime and
                        key in aliases):
                    if metadata["dataset_id"] in self.matched_worlds:
                        self.matched_worlds[metadata["dataset_id"]][key] = metadata["variable"]
                    else:
                        self.matched_worlds[metadata["dataset_id"]] = {key: metadata["variable"]}


    def __find_cmems_worlds(self, key: str):
        """
        Traverses CMEMS catalog and find products/datasets that match the glider sensors and
        the trajectory spatial and temporal extent.

        Parameters:
        - key: string that represents the variable to find

        Returns:
        - matched worlds dictionary containing dataset ids and variable names that reside within it.
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
                                # get time values either as part of values list or as a specific max and min value
                                # both are possibilities it seems!
                                try:
                                    start = variables[m]["coordinates"][n]["values"][0]
                                    end = variables[m]["coordinates"][n]["values"][-1]
                                    step = variables[m]["coordinates"][n]["values"][1] - \
                                           variables[m]["coordinates"][n]["values"][0]
                                except TypeError:
                                    start = variables[m]["coordinates"][n]["minimum_value"]
                                    end = variables[m]["coordinates"][n]["maximum_value"]
                                    step = variables[m]["coordinates"][n]["step"]
                                # convert trajectory datetimes into timestamps to be able to compare with CMEMS catalog
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

    def __get_msm_worlds(self,key: str,value):
        """

        Args:
            key: string the represents the source name
            value: object that contains the intake entry of the matched dataset

        Returns:
            lazy loaded xarray dataset
        """
        vars2 = []
        for k2,v2 in value.items():
            vars2.append(v2)
        zarr_f = (f"{key}_{self.extent.max_lng}_{self.extent.min_lng}_{self.extent.max_lat}_{self.extent.min_lat}_"
                  f"{self.extent.max_depth}_{self.extent.start_time}_{self.extent.end_time}.zarr")
        zarr_d = "msm-data/"
        if not os.path.isdir(zarr_d + zarr_f):
            data = self.catalog.msm_cat[str(key)].to_dask()
            # Assuming ds is your dataset, and lat/lon are 2D arrays with dimensions (y, x)
            lat = data['nav_lat']  # 2D latitude array (y, x)
            lon = data['nav_lon']  # 2D longitude array (y, x)
            # Step 1: Flatten lat/lon arrays and get the x, y indices
            lat_flat = lat.values.flatten()
            lon_flat = lon.values.flatten()
            # Step 2: Calculate the squared Euclidean distance for each point on the grid
            distance = np.sqrt((lat_flat - self.extent.max_lat) ** 2 + (lon_flat - self.extent.max_lng) ** 2)
            distance2 = np.sqrt((lat_flat - self.extent.min_lat) ** 2 + (lon_flat - self.extent.min_lng) ** 2)
            # Step 3: Find the index of the minimum distance
            min_index = np.argmin(distance)
            min_index2 = np.argmin(distance2)
            # Step 4: Convert the flattened index back to 2D indices
            y_size, x_size = lat.shape  # Get the shape of the 2D grid
            y_index_max, x_index_max = np.unravel_index(min_index, (y_size, x_size))
            y_index_min, x_index_min = np.unravel_index(min_index2, (y_size, x_size))
            subset = data.sel(y=slice(y_index_min,y_index_max), x=slice(x_index_min,x_index_max),deptht=slice(0,self.extent.max_depth),time_counter=slice(self.extent.start_time,self.extent.end_time))
            subset.to_zarr(store=zarr_d + zarr_f,safe_chunks=False)
        return zarr_d + zarr_f

    def __get_cmems_worlds(self, key, value):
        """
        Checks for the presence of, or downloads if not present the required subset of CMEMS catalog

        Parameters
        - key: string that represents the cmems dataset id
        - value: dictionary that contains the variable names to download

        Returns:
        string that represents the zarr store location of the downloaded data

        """

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


