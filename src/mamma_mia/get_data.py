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
import os
import tomllib

import copernicusmarine
import numpy as np
import xarray as xr
from loguru import logger
from OceanDataStore import OceanDataCatalog


def get_extent(spec_file: str) -> dict:
    """
    Download model data for the extent defined in a TOML specification file.

    Reads spatial and temporal extent parameters from the specification file,
    retrieves the corresponding model data, and returns a dictionary mapping
    each data source to its local path or storage location.

    Parameters
    ----------
    spec_file : str
        Path to the TOML specification file defining the spatial domain,
        time range, and data sources to retrieve.

    Returns
    -------
    dict
        Mapping of data source names to their local file paths or storage
        locations for use with `create_interpolator`.
    """
    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]
    sensors = spec["sensors"]
    geospatial_attrs = spec["environment"]["extent"]
    stores = __download_data(sensors=sensors, geospatial_attrs=geospatial_attrs)

    return stores


def get_data(mission: xr.DataTree) -> xr.DataTree:
    """
    Download model data for the spatial and temporal extent of a mission.

    Derives the required spatial domain and time range from the mission
    trajectory, retrieves the corresponding model data, and returns the
    mission DataTree updated with the paths or storage locations of the
    downloaded data.

    Parameters
    ----------
    mission : xr.DataTree
        A mission DataTree as returned by `create_mission`, from which
        trajectory-derived spatial and temporal extent attributes are read
        to determine the data download bounds.

    Returns
    -------
    xr.DataTree
        The input mission DataTree with top-level attributes updated to
        include the paths or storage locations of the downloaded model
        data, suitable for passing to `create_interpolator`.
    """
    logger.info("getting data as specified in mission attributes")
    sensors = mission["platform"].attrs["sensors"]
    stores = __download_data(sensors=sensors, geospatial_attrs=mission.attrs)
    mission.attrs.update(stores=stores)
    logger.success("data acquired successfully")
    return mission


def __download_data(sensors, geospatial_attrs):
    """
    core download component, goes through sensor entries and downloads data based its specification
    """
    source_ids = {}
    stores = {}
    for sensor in sensors.values():
        # go through each variable in the sensor
        for variable_key, variable in sensor.items():
            if variable["source_id"] == "":
                logger.warning(f"no source id found for {variable_key}")
                continue
            # build a dictionary that matches variables to models (e.g. thetao,so are in same dataset)
            source_id = variable["source_id"]

            if source_id in source_ids:
                source_ids[source_id]["variable_names"].append(
                    variable["variable_name"]
                )
                source_ids[source_id]["parameter_names"].append(variable_key)
            else:
                source_ids[source_id] = {
                    "variable_names": [variable["variable_name"]],
                    "parameter_names": [variable_key],
                }

        # download data using source id
        for source_id, source_var in source_ids.items():
            parts = source_id.split("-")
            parts2 = source_id.split("_")
            # if NOC datasource
            if parts[0] == "noc":
                store = __get_NOC(
                    source_id=source_id,
                    geospatial_attrs=geospatial_attrs,
                )
                regrid = True
            # if CMEMS datasource
            elif parts2[0] == "cmems":
                store = __get_cmems(
                    source_id=source_id,
                    variables=source_var["variable_names"],
                    geospatial_attrs=geospatial_attrs,
                )
                regrid = False
            # if its a file path
            elif parts[-1].endswith(".nc") or parts[-1].endswith(".zarr"):
                store = __get_local(
                    source_id=source_id,
                    variables=source_var["variable_names"],
                    geospatial_attrs=geospatial_attrs,
                )
                regrid = True
            else:
                raise Exception(f"unknown source id: {source_id}")
            # create a store location for each parameter (for interpoator)
            for i in range(source_var["parameter_names"].__len__()):
                stores[source_var["parameter_names"][i]] = {
                    "store": store,
                    "variable_name": source_var["variable_names"][i],
                    "regrid": regrid,
                }
    return stores


def __get_local(source_id, variables, geospatial_attrs):
    """
    check if local data file exists, has all the variables needed and contains
    the correct temporal and spatial extent
    """
    if os.path.isfile(source_id):
        logger.info(f"file found at source id path: {source_id}")
    else:
        raise Exception(f"no input data file found at location {source_id}")
    ds = xr.open_dataset(source_id)
    missing = [v for v in variables if v not in ds]
    if missing:
        raise Exception(f"Missing variables in dataset: {missing}")
    if not __check_subset(ds=ds, geospatial_attrs=geospatial_attrs):
        raise Exception("Dataset does not cover full extent of mission trajectory")
    return source_id


def __get_cmems(
    source_id, variables, geospatial_attrs, excess=0.5, excess_depth=100
) -> str:
    """
    cmems specific function to download data from CMEMS using copernicusmarinetoolbox
    """
    zarr_f = (
        f"{source_id}_{round(geospatial_attrs['geospatial_lon_max'] + excess, 3)}_{round(geospatial_attrs['geospatial_lon_min'] - excess, 3)}_"
        f"{round(geospatial_attrs['geospatial_lat_max'] + excess, 3)}_{round(geospatial_attrs['geospatial_lat_min'] - excess, 3)}_"
        f"{round(geospatial_attrs['geospatial_vertical_max'] + excess_depth, 3)}_{
            np.datetime_as_string(
                np.datetime64(geospatial_attrs['time_coverage_start'])
                - np.timedelta64(30, 'D'),
                unit='D',
            )
        }_"
        f"{
            np.datetime_as_string(
                np.datetime64(geospatial_attrs['time_coverage_end'])
                + np.timedelta64(30, 'D'),
                unit='D',
            )
        }.zarr"
    )

    zarr_d = "copernicus-data/"
    logger.info(f"getting cmems model {zarr_f}")
    if not os.path.isdir(zarr_d + zarr_f):
        logger.info(f"{zarr_f} has not been cached, downloading now")
        copernicusmarine.subset(
            dataset_id=source_id,
            variables=variables,
            minimum_longitude=float(geospatial_attrs["geospatial_lon_min"] - excess),
            maximum_longitude=float(geospatial_attrs["geospatial_lon_max"] + excess),
            minimum_latitude=float(geospatial_attrs["geospatial_lat_min"] - excess),
            maximum_latitude=float(geospatial_attrs["geospatial_lat_max"] + excess),
            start_datetime=str(
                np.datetime_as_string(
                    np.datetime64(geospatial_attrs["time_coverage_start"])
                    - np.timedelta64(30, "D"),
                    unit="D",
                )
            ),
            end_datetime=str(
                np.datetime_as_string(
                    np.datetime64(geospatial_attrs["time_coverage_end"])
                    + np.timedelta64(30, "D"),
                    unit="D",
                )
            ),
            minimum_depth=0,
            maximum_depth=float(
                geospatial_attrs["geospatial_vertical_max"] + excess_depth
            ),
            output_filename=zarr_f,
            output_directory=zarr_d,
            file_format="zarr",
        )
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f


def __get_NOC(source_id, geospatial_attrs, excess=0.5) -> str:
    """
    NOC specific function to download data from OceanDataStore
    """
    catalog = OceanDataCatalog(catalog_name="noc-model-stac")
    zarr_f = (
        f"{source_id}_{round(geospatial_attrs['geospatial_lon_max'] + excess, 3)}_{round(geospatial_attrs['geospatial_lon_min'] - excess, 3)}_"
        f"{round(geospatial_attrs['geospatial_lat_max'] + excess, 3)}_{
            round(geospatial_attrs['geospatial_lat_min'] - excess, 3)
        }_{
            np.datetime_as_string(
                np.datetime64(geospatial_attrs['time_coverage_start'])
                - np.timedelta64(30, 'D'),
                unit='D',
            )
        }_"
        f"{
            np.datetime_as_string(
                np.datetime64(geospatial_attrs['time_coverage_end'])
                + np.timedelta64(30, 'D'),
                unit='D',
            )
        }.zarr"
    )
    zarr_d = "NOC-data/"
    logger.info(f"getting NOC world {zarr_f}")
    if not os.path.isdir(zarr_d + zarr_f):
        logger.info(f"{zarr_f} has not been cached, downloading now")
        ds = catalog.open_dataset(
            id=source_id,
            start_datetime=str(
                np.datetime_as_string(
                    np.datetime64(geospatial_attrs["time_coverage_start"])
                    - np.timedelta64(30, "D"),
                    unit="D",
                )
            ),
            end_datetime=str(
                np.datetime_as_string(
                    np.datetime64(geospatial_attrs["time_coverage_end"])
                    + np.timedelta64(30, "D"),
                    unit="D",
                )
            ),
            bbox=(
                float(geospatial_attrs["geospatial_lon_min"] - excess),
                float(geospatial_attrs["geospatial_lat_min"] - excess),
                float(geospatial_attrs["geospatial_lon_max"] + excess),
                float(geospatial_attrs["geospatial_lat_max"] + excess),
            ),
        )
        ds.drop_encoding().to_zarr(store=zarr_d + zarr_f)
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f


def __check_subset(
    ds: xr.Dataset,
    geospatial_attrs: dict,
    fill_value: int = -1,
) -> bool:
    """
    Checks the input dataset to ensure the whole required extent fits within it.

    Args:
        ds: xarray dataset
        extent: WorldExtent object
        time_start: start of required temporal extent (DD/MM/YYYYTHH:MM:SS)
        time_end: end of required temporal extent (DD/MM/YYYYTHH:MM:SS)
        fill_value: fill value to exclude from bounds calculation
    Returns:
        True if the dataset covers the full extent, False otherwise
    Raises:
        ValueError: if no valid lat/lon values are found in the dataset
    """

    lat = ds["nav_lat"].values
    lon = ds["nav_lon"].values

    valid_mask = ~np.isclose(lat, fill_value) & ~np.isclose(lon, fill_value)
    lat_valid = lat[valid_mask]
    lon_valid = lon[valid_mask]

    if lat_valid.size == 0 or lon_valid.size == 0:
        raise ValueError(
            f"No valid lat/lon values found in dataset after excluding fill value ({fill_value})."
        )

    ds_bounds = {
        "lat": (float(lat_valid.min()), float(lat_valid.max())),
        "lon": (float(lon_valid.min()), float(lon_valid.max())),
        "time": (ds["time_counter"].values.min(), ds["time_counter"].values.max()),
    }

    requested_time_start = np.datetime64(geospatial_attrs["time_coverage_start"])

    requested_time_end = np.datetime64(geospatial_attrs["time_coverage_end"])

    return (
        ds_bounds["lat"][0] <= geospatial_attrs["geospatial_lat_min"]
        and ds_bounds["lat"][1] >= geospatial_attrs["geospatial_lat_max"]
        and ds_bounds["lon"][0] <= geospatial_attrs["geospatial_lon_min"]
        and ds_bounds["lon"][1] >= geospatial_attrs["geospatial_lon_max"]
        and ds_bounds["time"][0] <= requested_time_start
        and ds_bounds["time"][1] >= requested_time_end
    )
