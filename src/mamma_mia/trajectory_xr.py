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

# TODO need to add a spec file validator, e.g. range is list len 2, etc.


def _parse_time(values) -> np.ndarray:
    series = pd.Series(values)
    if pd.api.types.is_datetime64_any_dtype(series):
        return np.asarray(series, dtype="datetime64[ns]")
    return np.asarray(
        pd.to_datetime(series, format="%d/%m/%Y %H:%M:%S"), dtype="datetime64[ns]"
    )


def _validate_nan_distribution(
    data: np.ndarray,
    time: np.ndarray,
    name: str,
    max_nan_fraction: float = 0.75,
    n_segments: int = 4,
    min_valid_per_segment: int = 1,
) -> None:
    """
    Validate NaN distribution relative to the actual time axis.

    Segments are defined by equal time spans (not equal index counts),
    so irregular sampling is handled correctly.
    """
    if data.size == 0:
        raise ValueError(f"'{name}': array is empty.")

    nan_mask = np.isnan(data)
    nan_fraction = nan_mask.sum() / data.size

    if nan_fraction > max_nan_fraction:
        raise ValueError(
            f"'{name}': {nan_fraction:.1%} of values are NaN, "
            f"exceeds the maximum allowed fraction of {max_nan_fraction:.1%}."
        )

    # Build equal-width time segment boundaries
    t = time.astype("datetime64[ns]").astype(np.int64)  # ns integers for arithmetic
    t_edges = np.linspace(t[0], t[-1], n_segments + 1)

    for i in range(n_segments):
        in_segment = (t >= t_edges[i]) & (t < t_edges[i + 1])
        # Include the final point in the last segment
        if i == n_segments - 1:
            in_segment = (t >= t_edges[i]) & (t <= t_edges[i + 1])

        valid_count = (~nan_mask[in_segment]).sum()
        if valid_count < min_valid_per_segment:
            t_start = pd.Timestamp(int(t_edges[i])).isoformat()
            t_end = pd.Timestamp(int(t_edges[i + 1])).isoformat()
            raise ValueError(
                f"'{name}': time segment {i + 1}/{n_segments} "
                f"({t_start} → {t_end}) contains only {valid_count} valid "
                f"point(s), but at least {min_valid_per_segment} is required. "
                f"Valid data may be clustered rather than spread across the input."
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

        # Open dataset
        path = spec["trajectory"]["path"]
        if path[-3:] == ".nc":
            ds = xr.open_dataset(path)
        elif path[-4:] == ".csv":
            ds = pd.read_csv(path)
        elif path[-5:] == ".zarr":
            ds = xr.open_dataset(path, engine="zarr")
        else:
            extension = path.split(".")[-1]
            raise Exception(f"trajectory file type: {extension} is not supported")

        lat = np.array(ds[spec["navigation"]["latitude"]], dtype=np.float64)
        lon = np.array(ds[spec["navigation"]["longitude"]], dtype=np.float64)
        depth = np.array(ds[spec["navigation"]["depth"]], dtype=np.float64)

        time = _parse_time(ds[spec["navigation"]["time"]])
        logger.info("checking NaN's in trajectory")
        _validate_nan_distribution(lat, time, "latitude")
        _validate_nan_distribution(lon, time, "longitude")
        _validate_nan_distribution(depth, time, "depth")
        logger.success("NaN validation successful")
        coords = {
            "time": _parse_time(ds[spec["navigation"]["time"]]),
            "latitude": ("time", lat),
            "longitude": ("time", lon),
            "depth": ("time", depth),
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
