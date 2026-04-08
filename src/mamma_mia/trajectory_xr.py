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
import pandas as pd
import xarray as xr
from loguru import logger

from mamma_mia.sensors_xr import sensors


def _find_key(ds, keys, required=True):
    # in the case with no dataset return None so an empty trajectory is created
    if ds is None:
        return None

    matched = next((key for key in keys if key in ds), None)

    if matched is None:
        if required:
            assert False, (
                f"No matching key found: {set(keys)}\nAvailable keys: {set(ds.keys())}"
            )
        else:
            logger.warning(f"No matching key found for: {set(keys)}")

    return matched


def _parse_time(values) -> np.ndarray:
    series = pd.Series(values)
    if pd.api.types.is_datetime64_any_dtype(series):
        return np.asarray(series, dtype="datetime64[ns]")
    return np.asarray(
        pd.to_datetime(series, format="%d/%m/%Y %H:%M:%S"), dtype="datetime64[ns]"
    )


def create_trajectory(path: str | None):
    if path is None:
        coords = {
            "time": np.array(-999.999),
            "latitude": np.array(-999.999),
            "longitude": np.array(-999.999),
            "depth": np.array(-999.999),
        }
        data_vars = {
            "pitch": np.array(-999.999),
            "roll": np.array(-999.999),
            "yaw": np.array(-999.999),
        }

        return xr.Dataset(data_vars=data_vars, coords=coords)

    else:
        # open dataset
        if path[-3:] == ".nc":
            ds = xr.open_dataset(path)
        elif path[-4:] == ".csv":
            ds = pd.read_csv(path)
        elif path[-5:] == ".zarr":
            ds = xr.open_dataset(path)
        else:
            extension = path.split(".")[-1]
            raise Exception(f"trajectory file type: {extension} is not supported")

        time_key = _find_key(ds, sensors["data_logger"]["time"]["aliases"])
        lat_key = _find_key(ds, sensors["data_logger"]["latitude"]["aliases"])
        lon_key = _find_key(ds, sensors["data_logger"]["longitude"]["aliases"])
        depth_key = _find_key(ds, sensors["data_logger"]["depth"]["aliases"])
        pitch_key = _find_key(
            ds, sensors["data_logger"]["pitch"]["aliases"], required=False
        )
        roll_key = _find_key(
            ds, sensors["data_logger"]["roll"]["aliases"], required=False
        )
        yaw_key = _find_key(
            ds, sensors["data_logger"]["heading"]["aliases"], required=False
        )

        coords = {
            "time": _parse_time(ds[time_key]),
            "latitude": ("time", np.array(ds[lat_key], dtype=np.float64)),
            "longitude": ("time", np.array(ds[lon_key], dtype=np.float64)),
            "depth": ("time", np.array(ds[depth_key], dtype=np.float64)),
        }

        data_vars = {}
        if pitch_key is not None:
            data_vars["pitch"] = ("time", np.array(ds[pitch_key], dtype=np.float64))
        if roll_key is not None:
            data_vars["roll"] = ("time", np.array(ds[roll_key], dtype=np.float64))
        if yaw_key is not None:
            data_vars["yaw"] = ("time", np.array(ds[yaw_key], dtype=np.float64))

        return xr.Dataset(data_vars=data_vars, coords=coords)
