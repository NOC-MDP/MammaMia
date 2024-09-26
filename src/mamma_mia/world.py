from typing import Dict

from mamma_mia.trajectory import Trajectory
from mamma_mia.realities import Reality
import numpy as np
import os
import xarray as xr
import pyinterp.backends.xarray
from dataclasses import dataclass, asdict
# TODO figure out a unified approach to aliases
from mamma_mia.cmems_alias import alias
import copernicusmarine
import intake
from datetime import datetime
import xesmf as xe
from loguru import logger

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

    def __init__(self, trajectory: Trajectory, excess_space: int = 0.5, excess_depth: int = 100):
        self.max_lat = np.around(np.max(trajectory.latitudes), 2) + excess_space
        self.min_lat = np.around(np.min(trajectory.latitudes), 2) - excess_space
        self.max_lng = np.around(np.max(trajectory.longitudes), 2) + excess_space
        self.min_lng = np.around(np.min(trajectory.longitudes), 2) - excess_space
        # TODO dynamcially set the start and end times based on the model temporal resoltution e.g. monthly or daily as interpolation needs at least two time steps
        self.start_time = np.datetime_as_string(trajectory.datetimes[0] - np.timedelta64(30, 'D'), unit="D")
        self.end_time = np.datetime_as_string(trajectory.datetimes[-1] + np.timedelta64(30, 'D'), unit="D")
        self.max_depth = np.around(np.max(trajectory.depths), 2) + excess_depth

    def to_dict(self):
        return {k: str(v) for k, v in asdict(self).items()}

@dataclass
class Cats:
    """
    Catalog class
    """
    cmems_cat: dict
    msm_cat: intake.Catalog
    priorities: dict

    # TODO add in some kind of update check so that the json file is updated periodically
    # TODO need some kind of refresh option that will delete caches of downloaded data. (user enabled and probably if data is older than x?)
    def __init__(self, cat_path:str, search: str = "GLOBAL",overwrite=False,msm_priority:int=2,cmems_priority:int=1):
        self.cmems_cat = copernicusmarine.describe(contains=[search], include_datasets=True,
                                                   overwrite_metadata_cache=overwrite)
        self.msm_cat = intake.open_catalog(cat_path)
        self.priorities = {"msm":msm_priority,"cmems":cmems_priority}


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

    def __init__(self, trajectory: Trajectory, reality: Reality,cat_path:str="https://noc-msm-o.s3-ext.jc.rl.ac.uk/mamma-mia/catalog/catalog.yml" ):
        logger.info("reading catalogs")
        self.catalog = Cats(cat_path=cat_path)
        logger.success("catalogs loaded successfully")
        logger.info("building extent")
        self.extent = Extent(trajectory=trajectory)
        logger.success("extent built")
        self.matched_worlds = {}
        # TODO need to ensure any existing datasets that has been downloaded previously contain the required variables as a different sensorsuite could have been used
        self.__find_worlds(reality=reality)
        ds = {}
        for key, value in self.matched_worlds.items():
            store = self.__get_worlds(key=key, value=value)
            # Create the ds using the separate method
            ds[key] = (xr.open_zarr(store=store))
        logger.success("world get completed successfully")
        # Initialize the base class with the created group attributes
        super().__init__(ds)
        self.interpolator = {"priorities": {}}
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
            logger.info(f"searching worlds for key {key}")
            self.__find_cmems_worlds(key=key)
            self.__find_msm_worlds(key=key)
        logger.success("world search completed successfully")


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
            logger.error("unknown model source key")
            raise Exception
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
            logger.info(f"building worlds for dataset {key}")
            # for every variable
            for var in self[key]:
                logger.info(f"building world for variable {var}")
                # for each item in matched dictionary
                for k1, v1, in self.matched_worlds[key].items():
                    # if variable names match (this is to ensure variable names are consistent)
                    if var == v1:
                        split_key = key.split("_")
                        if split_key[0] == "msm":
                            if self.__check_priorities(key=k1,source="msm"):
                                continue
                            # rename time and depth dimensions to be consistent
                            ds = self[key][var].rename({"deptht": "depth","time_counter": "time"})
                            lat = ds['nav_lat']
                            lon = ds['nav_lon']
                            # Define a regular grid with 1D lat/lon arrays
                            target_lat = np.linspace(lat.min(), lat.max(),20)
                            target_lon = np.linspace(lon.min(), lon.max(),14)
                            # Create a target grid dataset
                            target_grid = xr.Dataset({
                                'latitude': (['latitude'], target_lat),
                                'longitude': (['longitude'], target_lon)
                            })
                            # Create a regridder object to go from curvilinear to regular grid
                            regridder = xe.Regridder(ds, target_grid, method='bilinear')
                            # Regrid the entire dataset
                            ds_regridded = regridder(ds)
                            # Add units to latitude and longitude coordinates
                            ds_regridded['latitude'].attrs['units'] = 'degrees_north'
                            ds_regridded['longitude'].attrs['units'] = 'degrees_east'
                            # Convert all float32 variables in the dataset to float64
                            ds_regridded = ds_regridded.astype('float64')
                            ds_regridded['time'] = ds_regridded['time'].astype('datetime64[ns]')
                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(ds_regridded,geodetic=True)
                            # create or update priorities of interpolator datasetsc
                            self.interpolator["priorities"][k1] = self.catalog.priorities["msm"]
                        elif split_key[0] == "cmems":
                            if self.__check_priorities(key=k1,source="cmems"):
                                continue
                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(self[key][var],geodetic=True)
                            self.interpolator["priorities"][k1] = self.catalog.priorities["cmems"]
                        else:
                            logger.error("unknown model source key")
                            raise Exception
                        logger.info(f"built {var} from source {split_key[0]} into interpolator: {k1}")
        logger.success("world build completed successfully")

    def __find_msm_worlds(self, key:str):
        """

        Args:
            key: string that represents the variable to find

        Returns:
            matched worlds dictionary containing dataset ids and variable names

        """
        for k1,v1 in self.catalog.msm_cat.items():
            var_key = None
            logger.info(f"searching {k1}")
            metadata = v1.describe()['metadata']
            aliases = metadata.get('aliases', [])
            # check if the key is in one of the variables alias dictionaries
            for k2,v2 in aliases.items():
                if key in v2:
                    var_key = k2
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
                        start_traj >= start_datetime and end_traj <= end_datetime and var_key is not None):
                    logger.success(f"found a match in {k1} for {key}")
                    if k1 in self.matched_worlds:
                        logger.info(f"updating {k1} with key {key}")
                        self.matched_worlds[k1][key] = var_key
                    else:
                        logger.info(f"creating new matched world {k1} for key {key}")
                        self.matched_worlds[k1] = {key: var_key}


    def __find_cmems_worlds(self, key: str):
        """
        Traverses CMEMS catalog and find products/datasets that match the glider sensors and
        the trajectory spatial and temporal extent.

        Parameters:
        - key: string that represents the variable to find

        Returns:
        - matched worlds dictionary containing dataset ids and variable names that reside within it.
        """
        for k1, v1 in self.catalog.cmems_cat.items():
            logger.info(f"searching cmems {k1}")
            for i in range(len(v1)):
                # ensure it is a numerical model
                if v1[i]["sources"][0] != "Numerical models":
                    logger.warning(f"{v1[i]['sources'][0]} is not a numerical model")
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
                                        logger.success(f"found a match in {dataset['dataset_id']} for {key}")
                                        if dataset["dataset_id"] in self.matched_worlds:
                                            logger.info(f"updating {dataset['dataset_id']} with key {key}")
                                            self.matched_worlds[dataset["dataset_id"]][key] = variables[m]["short_name"]
                                        else:
                                            logger.info(f"creating new matched world {dataset['dataset_id']} for key {key}")
                                            self.matched_worlds[dataset["dataset_id"]] = {
                                                key: variables[m]["short_name"]}

    def __get_msm_worlds(self,key: str,value):
        """

        Args:
            key: string the represents the source name
            value: object that contains the intake entry of the matched dataset

        Returns:
            string that represents the zarr store location of the downloaded data
        """
        var_str = ""
        vars2 = []
        for k2,v2 in value.items():
            vars2.append(v2)
            var_str = var_str+str(v2)+"_"
        # TODO add in a min depth parameter? or always assume its the surface?
        zarr_f = (f"{key}_{var_str}{self.extent.max_lng}_{self.extent.min_lng}_{self.extent.max_lat}_{self.extent.min_lat}_"
                  f"{self.extent.max_depth}_{self.extent.start_time}_{self.extent.end_time}.zarr")
        zarr_d = "msm-data/"
        logger.info(f"getting msm world {zarr_f}")
        if not os.path.isdir(zarr_d + zarr_f):
            logger.info(f"{zarr_f} has not been cached, downloading now")
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
            subset = data[vars2].sel(y=slice(y_index_min,y_index_max), x=slice(x_index_min,x_index_max),deptht=slice(0,self.extent.max_depth),time_counter=slice(self.extent.start_time,self.extent.end_time))
            subset.to_zarr(store=zarr_d + zarr_f,safe_chunks=False)
            logger.success(f"{zarr_f} has been cached")
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
        logger.info(f"getting cmems world {zarr_f}")
        if not os.path.isdir(zarr_d + zarr_f):
            logger.info(f"{zarr_f} has not been cached, downloading now")
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
            logger.success(f"{zarr_f} has been cached")
        return zarr_d + zarr_f

    def __check_priorities(self,key:str,source:str) -> bool:
        if source not in ["msm", "cmems"]:
            logger.error(f"unknown source: {source}")
            raise Exception
        if key in self.interpolator["priorities"]:
            logger.warning(f"reality parameter {key} already exists, checking priority of data source with existing dataset")
            if self.interpolator["priorities"][key] > self.catalog.priorities[source]:
                logger.info(f"data source {source} is a lower priority, skipping world build")
                return True
            logger.info(f"data source {source} is a higher priority, updating world build")
        return False

