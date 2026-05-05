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

from typing import Union, overload

import numpy as np
import pyinterp
import pyinterp.backends.xarray
import xarray as xr
import xesmf as xe
from loguru import logger


def interpolate(
    interpolators: dict,
    coords: dict,
) -> dict:
    """
    Interpolate geophysical fields at the given coordinates.

    Parameters
    ----------
    interpolators : dict
        Mapping of field names to interpolator objects, where each interpolator
        accepts spatial and temporal coordinates and returns sampled values.
    coords : dict
        Sampling coordinates at which to evaluate each interpolator. Values may
        be single floats or datetime strings, lists of floats or datetime
        strings, or NumPy arrays of ``float64`` or ``datetime64[ns]``.
        Expected keys:

        .. code-block:: python

            {
                "latitude":  [26.834],
                "longitude": [-15.142],
                "depth":     [25.0],
                "time":      ["2023-03-03T00:00:00"],
            }

    Returns
    -------
    dict
        Mapping of field names to interpolated values, with one output entry
        per interpolator keyed by the same name.
    """
    dtypes = {"time": "datetime64[ns]"}
    # convert input values into numpy arrays if they aren't already
    numpy_point = {
        k: np.atleast_1d(np.asarray(v, dtype=dtypes.get(k))) for k, v in coords.items()
    }
    # run through interpolator
    interpolated_data = {
        key: interp.quadrivariate(numpy_point) for key, interp in interpolators.items()
    }

    return interpolated_data


@overload
def create_interpolator(mission: xr.DataTree) -> dict: ...


@overload
def create_interpolator(mission: list[xr.DataTree]) -> list[dict]: ...


@overload
def create_interpolator(mission: dict) -> dict: ...


def create_interpolator(
    mission: Union[xr.DataTree, list[xr.DataTree], dict],
) -> Union[dict, list[dict]]:
    if isinstance(mission, dict):
        return _create_interpolator(stores=mission)
    elif isinstance(mission, list):
        return [_create_interpolator(mission=m) for m in mission]
    else:
        return _create_interpolator(mission=mission)


def _create_interpolator(mission: xr.DataTree | None = None, stores: dict = {}) -> dict:
    """
    Create a pyinterp 4D interpolator covering all downloaded data stores.

    Interpolators are built from store attributes sourced either from a mission
    DataTree (which includes a trajectory node) or from a bare stores dictionary
    produced by a simulator integration. If any data source requires regridding,
    this is performed internally before the interpolator is constructed.

    Parameters
    ----------
    mission : xr.DataTree, optional
        A mission DataTree as returned by `create_mission`, from which store
        attributes and trajectory information are extracted. Must contain a
        trajectory node with associated data store metadata. Either `mission`
        or `stores` must be provided.
    stores : dict, optional
        A dictionary of data stores generated directly by a simulator
        integration, used as an alternative to providing a full mission
        DataTree. Either `mission` or `stores` must be provided.

    Returns
    -------
    dictionary containing pyinterp interpolators
        A 4D interpolator (latitude, longitude, depth, time) constructed
        for all available data stores, ready to be passed to `fly` or
        `interpolate`.
    """
    if mission is not None:
        logger.info(f"creating interpolator for mission {mission.attrs['name']}")
    else:
        logger.info("creating interpolator")
    # empty dict evaluates to false
    if not stores:
        if mission is None:
            raise ValueError("Either mission or stores must be provided")
        stores = mission.attrs["stores"]
    interpolator = {}
    for store_key, store in stores.items():
        if store["store"].endswith(".nc"):
            ds = xr.open_dataset(store["store"])
        elif store["store"].endswith(".zarr"):
            ds = xr.open_zarr(store=store["store"])
        else:
            raise Exception(f"unknown store {store['store']}")
        # if regridding is needed
        if stores[store_key]["regrid"]:
            logger.info(
                f"dataset {stores[store_key]['store']} needs regridding, performing now"
            )
            if ds["nav_lat"].sizes["x"] == 1:
                logger.warning(
                    "dataset latitude dimension length = 1, cannot interpolate, likely too low resolution"
                )
                continue
            if ds["nav_lon"].sizes["x"] == 1:
                logger.warning(
                    "dataset longitude dimension length = 1, cannot interpolate, likely too low resolution"
                )
                continue
            if ds["time_counter"].sizes["time_counter"] <= 1:
                logger.warning(
                    "dataset time dimension length = 1, cannot interpolate, likely too low resolution"
                )
                continue
            # rename time and depth dimensions to be consistent
            # depths can be named t u or v depending on their grid
            # rename time and depth dimensions to be consistent
            # depths can be named t, u, v, or w depending on their grid
            depth_variants = ["deptht", "depthu", "depthv", "depthw"]
            depth_dim = next((d for d in depth_variants if d in ds.dims), None)

            if depth_dim is None:
                raise ValueError(
                    f"No recognised depth dimension found. Got: {list(ds.dims)}"
                )

            ds = ds.rename(
                {
                    depth_dim: "depth",
                    "time_counter": "time",
                    "nav_lon": "lon",
                    "nav_lat": "lat",
                }
            )

            lat = ds["lat"]
            lon = ds["lon"]

            # reduce arrays to get max and min values
            latmin = lat.reduce(np.min, dim=["x", "y"]).values
            latmax = lat.reduce(np.max, dim=["x", "y"]).values
            lonmin = lon.reduce(np.min, dim=["x", "y"]).values
            lonmax = lon.reduce(np.max, dim=["x", "y"]).values
            # Define a regular grid with 1D lat/lon arrays
            target_lat = np.linspace(latmin, latmax, lat.sizes["y"])
            target_lon = np.linspace(lonmin, lonmax, lon.sizes["x"])
            # Create a target grid dataset
            target_grid = xr.Dataset(
                {
                    "latitude": (["latitude"], target_lat),
                    "longitude": (["longitude"], target_lon),
                }
            )
            # Example: regrid only data variables that depend on lat/lon
            data_vars = [v for v in ds.data_vars if {"x", "y"} <= set(ds[v].dims)]
            # Loop and regrid each variable
            ds_regridded = xr.Dataset()
            for var2 in data_vars:
                if isinstance(var2, str) and "time" in var2:
                    continue
                regridder = xe.Regridder(
                    ds[var2], target_grid, method="bilinear", ignore_degenerate=True
                )
                ds_regridded[var2] = regridder(ds[var2])
            ds_regridded = ds_regridded.assign_coords(time=ds.time)

            # # Create a regridder object to go from curvilinear to regular grid
            # Add units to latitude and longitude coordinates
            ds_regridded["latitude"].attrs["units"] = "degrees_north"
            ds_regridded["longitude"].attrs["units"] = "degrees_east"
            # Convert all float32 variables in the dataset to float64 and rename to ds
            ds = ds_regridded.astype("float64")
            ds["time"] = ds["time"].astype("datetime64[ns]")
            logger.success("regridding successful")

        interpolator[store_key] = pyinterp.backends.xarray.Grid4D(
            ds[store["variable_name"]], geodetic=True
        )
    logger.success("interpolator created successfully")
    return interpolator
