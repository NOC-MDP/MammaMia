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

import tomllib

import numpy as np
import pandas as pd
import xarray as xr
from loguru import logger


def _parse_time(values) -> np.ndarray:
    series = pd.Series(values)
    if pd.api.types.is_datetime64_any_dtype(series):
        return np.asarray(series, dtype="datetime64[ns]")
    return np.asarray(
        pd.to_datetime(series, format="%d/%m/%Y %H:%M:%S"), dtype="datetime64[ns]"
    )


def create_trajectory(spec_file: str = "") -> xr.Dataset:
    if spec_file == "":
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
        with open(spec_file, "rb") as f:
            raw = tomllib.load(f)

        spec = raw["specification"]
        # open dataset
        path = spec["trajectory"]["path"]
        if path[-3:] == ".nc":
            ds = xr.open_dataset(path)
        elif path[-4:] == ".csv":
            ds = pd.read_csv(path)
        elif path[-5:] == ".zarr":
            ds = xr.open_dataset(path)
        else:
            extension = path.split(".")[-1]
            raise Exception(f"trajectory file type: {extension} is not supported")

        coords = {
            "time": _parse_time(ds[spec["navigation"]["time"]]),
            "latitude": (
                "time",
                np.array(ds[spec["navigation"]["latitude"]], dtype=np.float64),
            ),
            "longitude": (
                "time",
                np.array(ds[spec["navigation"]["longitude"]], dtype=np.float64),
            ),
            "depth": (
                "time",
                np.array(ds[spec["navigation"]["depth"]], dtype=np.float64),
            ),
        }

        data_vars = {}
        try:
            data_vars["pitch"] = (
                "time",
                np.array(ds[spec["navigation"]["pitch"]], dtype=np.float64),
            )
        except KeyError:
            logger.warning("pitch key not found in trajectory dataset")
        try:
            data_vars["roll"] = (
                "time",
                np.array(ds[spec["navigation"]["roll"]], dtype=np.float64),
            )
        except KeyError:
            logger.warning("roll key not found in trajectory dataset")
        try:
            data_vars["yaw"] = (
                "time",
                np.array(ds[spec["navigation"]["yaw"]], dtype=np.float64),
            )
        except KeyError:
            logger.warning("yaw key not found in trajectory dataset")
        return xr.Dataset(data_vars=data_vars, coords=coords)
