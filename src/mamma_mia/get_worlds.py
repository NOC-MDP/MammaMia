from mamma_mia.catalog import Cats
import numpy as np
from loguru import logger
import os
import copernicusmarine
import zarr
from mamma_mia.exceptions import UnknownSourceKey
import xarray as xr

def get_worlds(cat: Cats, world:zarr.Group) -> dict:
    """
    function that will get the worlds/model data as specified in the matched worlds attribute in the provided world zarr group.
    Args:
        cat: initialised Cats object that contains all the source data available to download
        world: worlds zarr group that contains an updated matched worlds attribute to allow model data to be downloaded

    Returns:
        dict: dictionary containing the locations of the downloaded model data zarr stores. The world zarr group is also
              returned populated with model data that matches the required spatial and temporal extents and is also
              valid for the specified sensors of the auv.

    """
    zarr_stores = {}
    for key, value in world.attrs["matched_worlds"].items():
        split_key = key.split("_")

        if split_key[0] == "cmems":
            zarr_store = __get_cmems_worlds(key=key, value=value,world=world)
            zarr_stores[key] = zarr_store
        elif split_key[0] == "msm":
            zarr_store = __get_msm_worlds(key=key, value=value, catalog=cat,world=world)
            zarr_stores[key] = zarr_store
        else:
            logger.error("unknown model source key")
            raise UnknownSourceKey
        zarr_source = zarr.open(zarr_store, mode='r')
        zarr.copy_all(source=zarr_source, dest=world[key])

    return zarr_stores

def __get_msm_worlds(key: str, value, catalog: Cats,world:zarr.Group) -> str:
    """
    Function that downloads the msm source model data that matches the required spatial and temporal extents and sensor
    specification of the auv.
    Args:
        key: model source
        value: object that contains the intake entry of the matched dataset
        world: zarr group that contains the world attributes and will store the downloaded model data

    Returns:
        string that represents the zarr store location of the downloaded data. The world zarr group is also updated with
        the downloaded model data.
    """
    var_str = ""
    vars2 = []
    subsets = []
    msm = world.create_group(key)
    msm.attrs["spatial_extent"] = {"max_lng": world.attrs["extent"]["max_lng"],
                                   "min_lng": world.attrs["extent"]["min_lng"],
                                   "max_lat": world.attrs["extent"]["max_lat"],
                                   "min_lat": world.attrs["extent"]["min_lat"],
                                   "max_depth": world.attrs["extent"]["max_depth"]}
    msm.attrs["temporal_extent"] = {"start_time": world.attrs["extent"]["start_time"],
                                    "end_time": world.attrs["extent"]["end_time"]}

    for k2, v2 in value.items():
        vars2.append(v2)
        var_str = var_str + str(v2) + "_"
    # TODO add in a min depth parameter? or always assume its the surface?
    zarr_f = (f"{key}_{var_str}{msm.attrs['spatial_extent']['max_lng']}_{msm.attrs['spatial_extent']['min_lng']}_"
              f"{msm.attrs['spatial_extent']['max_lat']}_{msm.attrs['spatial_extent']['min_lat']}_"
              f"{msm.attrs['spatial_extent']['max_depth']}_{msm.attrs['temporal_extent']['start_time']}_"
              f"{msm.attrs['temporal_extent']['end_time']}.zarr")
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
            distance = np.sqrt((lat_flat - msm.attrs['spatial_extent']['max_lat']) ** 2 + (
                        lon_flat - msm.attrs['spatial_extent']['max_lng']) ** 2)
            distance2 = np.sqrt((lat_flat - msm.attrs['spatial_extent']['min_lat']) ** 2 + (
                        lon_flat - msm.attrs['spatial_extent']['min_lng']) ** 2)
            # Step 3: Find the index of the minimum distance
            min_index = np.argmin(distance)
            min_index2 = np.argmin(distance2)
            # Step 4: Convert the flattened index back to 2D indices
            y_size, x_size = lat.shape  # Get the shape of the 2D grid
            y_index_max, x_index_max = np.unravel_index(min_index, (y_size, x_size))
            y_index_min, x_index_min = np.unravel_index(min_index2, (y_size, x_size))
            subsets.append(data[var].sel(y=slice(y_index_min, y_index_max),
                                     x=slice(x_index_min, x_index_max),
                                     deptht=slice(0, msm.attrs['spatial_extent']['max_depth']),
                                     time_counter=slice(msm.attrs['temporal_extent']['start_time'],
                                                        msm.attrs['temporal_extent']['end_time'])))
        subset = xr.merge(subsets)
        subset.to_zarr(store=zarr_d + zarr_f, safe_chunks=False)
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f


def __get_cmems_worlds(key: str, value,world:zarr.Group) -> str:
    """
    function that downloads model data from CMEMS, data must match the temporal and spatial extents of the auv, and also
    have the required variables to match the sensor arrays of the auv.
    Args:
        key: model source
        value: object that contains the intake entry of the matched dataset
        world: zarr group that contains the world attributes and will store the downloaded model data

    Returns:
        string that represents the zarr store location of the downloaded data. The world zarr group is also updated with
        the downloaded model data.

    """
    vars2 = []
    # pull out the var names that CMEMS needs NOTE not the same as Mamma Mia uses
    for k2, v2 in value.items():
        vars2.append(v2)
    cmems = world.create_group(key)
    cmems.attrs["spatial_extent"] = {"max_lng": world.attrs["extent"]["max_lng"],
                                     "min_lng": world.attrs["extent"]["min_lng"],
                                     "max_lat": world.attrs["extent"]["max_lat"],
                                     "min_lat": world.attrs["extent"]["min_lat"],
                                     "max_depth": world.attrs["extent"]["max_depth"]}
    cmems.attrs["temporal_extent"] = {"start_time": world.attrs["extent"]["start_time"],
                                      "end_time": world.attrs["extent"]["end_time"]}

    zarr_f = (f"{value['data_id']}_{cmems.attrs['spatial_extent']['max_lng']}_{cmems.attrs['spatial_extent']['min_lng']}_"
              f"{cmems.attrs['spatial_extent']['max_lat']}_{cmems.attrs['spatial_extent']['min_lat']}_"
              f"{cmems.attrs['spatial_extent']['max_depth']}_{cmems.attrs['temporal_extent']['start_time']}_"
              f"{cmems.attrs['temporal_extent']['end_time']}.zarr")
    zarr_d = "copernicus-data/"
    logger.info(f"getting cmems world {zarr_f}")
    if not os.path.isdir(zarr_d + zarr_f):
        logger.info(f"{zarr_f} has not been cached, downloading now")
        copernicusmarine.subset(
            dataset_id=value['data_id'],
            variables=value["variables"],
            minimum_longitude=cmems.attrs['spatial_extent']['min_lng'],
            maximum_longitude=cmems.attrs['spatial_extent']['max_lng'],
            minimum_latitude=cmems.attrs['spatial_extent']['min_lat'],
            maximum_latitude=cmems.attrs['spatial_extent']['max_lat'],
            start_datetime=str(cmems.attrs['temporal_extent']['start_time']),
            end_datetime=str(cmems.attrs['temporal_extent']['end_time']),
            minimum_depth=0,
            maximum_depth=cmems.attrs['spatial_extent']['max_depth'],
            output_filename=zarr_f,
            output_directory=zarr_d,
            file_format="zarr",
            force_download=True
        )
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f