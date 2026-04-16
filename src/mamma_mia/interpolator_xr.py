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

import numpy as np
import pyinterp
import pyinterp.backends.xarray
import xarray as xr
import xesmf as xe
from loguru import logger


def interpolate(interpolators: dict, point: dict):
    dtypes = {"time": "datetime64[ns]"}
    numpy_point = {
        k: np.atleast_1d(np.asarray(v, dtype=dtypes.get(k))) for k, v in point.items()
    }
    interpolated_data = {
        key: interp.quadrivariate(numpy_point) for key, interp in interpolators.items()
    }
    return interpolated_data


def create_interpolator(mission: xr.DataTree = None, stores: dict = None):
    if stores is None:
        if mission is None:
            raise ValueError("Either mission or stores must be provided")
        stores = mission.attrs["stores"]
    interpolator = {}
    for store_key, store in stores.items():
        ds = xr.open_zarr(store=store["store"])
        # if regridding is needed
        if stores[store_key]["regrid"]:
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
            try:
                ds = ds.rename(
                    {
                        "deptht": "depth",
                        "time_counter": "time",
                        "nav_lon": "lon",
                        "nav_lat": "lat",
                    }
                )
            except ValueError:
                try:
                    ds = ds.rename(
                        {
                            "depthu": "depth",
                            "time_counter": "time",
                            "nav_lon": "lon",
                            "nav_lat": "lat",
                        }
                    )
                except ValueError:
                    ds = ds.rename(
                        {
                            "depthv": "depth",
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
                if "time" in var2:
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

        interpolator[store_key] = pyinterp.backends.xarray.Grid4D(
            ds[store["variable_name"]], geodetic=True
        )
    return interpolator
