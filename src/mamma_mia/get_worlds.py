# Copyright 2025 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mamma_mia.worlds import SourceConfig,SourceType, WorldsConf
from mamma_mia.catalog import Cats
import numpy as np
from loguru import logger
import os
import copernicusmarine
import zarr
from mamma_mia.exceptions import UnknownSourceKey
import xarray as xr

def get_worlds(cat: Cats, worlds:WorldsConf,source:SourceConfig) -> dict:
    """
    function that will get the worlds/model data as specified in the matched worlds attribute in the provided world zarr group.
    Args:
        source:
        cat: initialised Cats object that contains all the source data available to download
        worlds:

    Returns:
        dict: dictionary containing the locations of the downloaded model data zarr stores. The world zarr group is also
              returned populated with model data that matches the required spatial and temporal extents and is also
              valid for the specified sensors of the auv.

    """
    zarr_stores = {}
    for key, value in worlds.attributes.matched_worlds.items():
        if source.source_type == SourceType.CMEMS:
            zarr_store = __get_cmems_worlds(value=value,worlds=worlds)
            zarr_stores[key] = zarr_store
            worlds.worlds[key] = zarr.open(zarr_store, mode='r')
        elif source.source_type == SourceType.MSM:
            zarr_store = __get_msm_worlds(key=key, value=value, catalog=cat,worlds=worlds)
            zarr_stores[key] = zarr_store
            worlds.worlds[key] = zarr.open(zarr_store, mode='r')
        elif source.source_type == SourceType.LOCAL:
            zarr_stores[key] = value.local_dir + "/" + value.data_id
            worlds.worlds[key] = xr.open_dataset(value.local_dir+"/"+value.data_id)
        else:
            logger.error(f"unknown model source {source.source_type}")
            raise UnknownSourceKey

    return zarr_stores

def __get_msm_worlds(key: str, value, catalog: Cats,worlds:WorldsConf) -> str:
    """
    Function that downloads the msm source model data that matches the required spatial and temporal extents and sensor
    specification of the auv.
    Args:
        key: model source
        value: object that contains the intake entry of the matched dataset
        worlds:

    Returns:
        string that represents the zarr store location of the downloaded data. The world zarr group is also updated with
        the downloaded model data.
    """
    var_str = ""
    vars2 = []
    subsets = []

    for k2, v2 in value.items():
        vars2.append(v2)
        var_str = var_str + str(v2) + "_"
    # TODO add in a min depth parameter? or always assume its the surface?
    zarr_f = (f"{value.data_id}_{worlds.attributes.extent.lon_max}_{worlds.attributes.extent.lon_min}_"
              f"{worlds.attributes.extent.lat_max}_{worlds.attributes.extent.lat_min}_"
              f"{worlds.attributes.extent.depth_max}_{worlds.attributes.extent.time_start}_"
              f"{worlds.attributes.extent.time_end}.zarr")
    zarr_d = "msm-data/"
    logger.info(f"getting msm world {zarr_f}")
    if not os.path.isdir(zarr_d + zarr_f):
        logger.info(f"{zarr_f} has not been cached, downloading now")
        for var in vars2:
            data = catalog.msm_cat[str(key)](var=var,grid="T",frequency="monthly").to_dask()
            # Assuming ds is your dataset, and lat/lon are 2D arrays with dimensions (y, x)
            lat = data['nav_lat']  # 2D latitude array (y, x)
            lon = data['nav_lon']  # 2D longitude array (y, x)
            # Step 1: Flatten lat/lon arrays and get the x, y indices
            lat_flat = lat.values.flatten()
            lon_flat = lon.values.flatten()
            # Step 2: Calculate the squared Euclidean distance for each point on the grid
            distance = np.sqrt((lat_flat - worlds.attributes.extent.lat_max) ** 2 + (
                        lon_flat - worlds.attributes.extent.lon_max) ** 2)
            distance2 = np.sqrt((lat_flat - worlds.attributes.extent.lat_min) ** 2 + (
                        lon_flat - worlds.attributes.extent.lon_min) ** 2)
            # Step 3: Find the index of the minimum distance
            min_index = np.argmin(distance)
            min_index2 = np.argmin(distance2)
            # Step 4: Convert the flattened index back to 2D indices
            y_size, x_size = lat.shape  # Get the shape of the 2D grid
            y_index_max, x_index_max = np.unravel_index(min_index, (y_size, x_size))
            y_index_min, x_index_min = np.unravel_index(min_index2, (y_size, x_size))
            subsets.append(data[var].sel(y=slice(y_index_min, y_index_max),
                                     x=slice(x_index_min, x_index_max),
                                     deptht=slice(0, worlds.attributes.extent.depth_max),
                                     time_counter=slice(worlds.attributes.extent.time_start,
                                                        worlds.attributes.extent.time_end)))
        subset = xr.merge(subsets)
        subset.to_zarr(store=zarr_d + zarr_f, safe_chunks=False)
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f


def __get_cmems_worlds(value,worlds:WorldsConf) -> str:
    """
    function that downloads model data from CMEMS, data must match the temporal and spatial extents of the auv, and also
    have the required variables to match the sensor arrays of the auv.
    Args:
        value: object that contains the intake entry of the matched dataset
        worlds:

    Returns:
        string that represents the zarr store location of the downloaded data. The world zarr group is also updated with
        the downloaded model data.

    """
    # vars2 = []
    # # pull out the var names that CMEMS needs NOTE not the same as Mamma Mia uses
    # for k2, v2 in value.items():
    #     vars2.append(v2)

    zarr_f = (f"{value.data_id}_{worlds.attributes.extent.lon_max}_{worlds.attributes.extent.lon_min}_"
              f"{worlds.attributes.extent.lat_max}_{worlds.attributes.extent.lat_min}_"
              f"{worlds.attributes.extent.depth_max}_{worlds.attributes.extent.time_start}_"
              f"{worlds.attributes.extent.time_end}.zarr")
    zarr_d = "copernicus-data/"
    logger.info(f"getting cmems world {zarr_f}")
    if not os.path.isdir(zarr_d + zarr_f):
        logger.info(f"{zarr_f} has not been cached, downloading now")
        copernicusmarine.subset(
            dataset_id=value.data_id,
            variables=list(value.variable_alias.keys()),
            minimum_longitude=float(worlds.attributes.extent.lon_min),
            maximum_longitude=float(worlds.attributes.extent.lon_max),
            minimum_latitude=float(worlds.attributes.extent.lat_min),
            maximum_latitude=float(worlds.attributes.extent.lat_max),
            start_datetime=str(worlds.attributes.extent.time_start),
            end_datetime=str(worlds.attributes.extent.time_end),
            minimum_depth=0,
            maximum_depth=float(worlds.attributes.extent.depth_max),
            output_filename=zarr_f,
            output_directory=zarr_d,
            file_format="zarr",
            force_download=True
        )
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f