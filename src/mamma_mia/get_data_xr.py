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
    gets model data using extent specificied in specification toml file
    and returns a dictionary detailing their paths/locations.
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
    gets model data using mission attributes derived from a trajectory dataset and
    updates mission attributes with paths/locations of downloaded data
    """
    sensors = mission["platform"].attrs["sensors"]
    geospatial_attrs = mission.attrs["geospatial_attrs"]
    stores = __download_data(sensors=sensors, geospatial_attrs=geospatial_attrs)
    mission.attrs.update(stores=stores)
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
            if parts[0] == "noc":
                store = __get_NOC(
                    source_id=source_id,
                    geospatial_attrs=geospatial_attrs,
                )
                regrid = True
            elif parts2[0] == "cmems":
                store = __get_cmems(
                    source_id=source_id,
                    variables=source_var["variable_names"],
                    geospatial_attrs=geospatial_attrs,
                )
                regrid = False
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


def __get_cmems(
    source_id, variables, geospatial_attrs, excess=0.5, excess_depth=100
) -> str:
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
    Function that downloads the NOC source model data that matches the required spatial and temporal extents and sensor
    specification of the auv.
    Args:
        key: model source
        worlds:

    Returns:
        string that represents the zarr store location of the downloaded data. The world zarr group is also updated with
        the downloaded model data.
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
