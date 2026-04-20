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


def __open_ds(path: str) -> xr.Dataset:
    if path[-3:] == ".nc":
        ds = xr.open_dataset(path)
    elif path[-4:] == ".csv":
        ds = pd.read_csv(path)
    elif path[-5:] == ".zarr":
        ds = xr.open_dataset(path, engine="zarr")
    else:
        extension = path.split(".")[-1]
        raise Exception(f"trajectory file type: {extension} is not supported")
    return ds


def __open_spec(spec_file: str) -> dict:
    """
    open toml file and return a dict containing specification
    """
    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    return raw["specification"]


def create_trajectories(spec_file: str) -> [xr.Dataset]:
    trajectories = []

    spec = __open_spec(spec_file)
    ds = __open_ds(path=spec["trajectory"]["path"])

    for i in range(ds["trajectory"].__len__()):
        ds_single_traj = ds.isel(trajectory=i)
        trajectories.append(create_trajectory(spec_file=spec_file, ds=ds_single_traj))
    return trajectories


def create_trajectory(spec_file: str, ds=None) -> xr.Dataset:
    """
    Create a trajectory Dataset from a TOML specification file.

    Reads navigation data from a source file (NetCDF, Zarr, or CSV) as
    specified in the TOML config, maps user-defined variable names to
    standardised navigation parameters, and interpolates any NaN values.
    Sufficient valid data between gaps is assumed for interpolation to
    produce reliable results.

    Parameters
    ----------
    spec_file : str
        Path to the TOML specification file, which defines the path to the
        source navigation data file, its format, and the mapping of variable
        names to standard navigation parameters (e.g. latitude, longitude,
        depth, time). Defaults to an empty string.

    Returns
    -------
    xr.Dataset
        A trajectory Dataset with standardised navigation parameter names
        and NaN values interpolated, compatible with the MAMMA MIA mission
        framework and suitable for passing to `create_mission`.
    """
    logger.info(f"creating a trajectory dataset using spec file {spec_file}")

    spec = __open_spec(spec_file)

    if ds is None:
        # Open dataset using spec file
        ds = __open_ds(path=spec["trajectory"]["path"])

    # Extract and clean navigation coordinates
    lat = np.array(ds[spec["navigation"]["latitude"]], dtype=np.float64)
    lon = np.array(ds[spec["navigation"]["longitude"]], dtype=np.float64)
    depth = np.array(ds[spec["navigation"]["depth"]], dtype=np.float64)
    time = _parse_time(ds[spec["navigation"]["time"]])

    # Interpolate any NaNs in the coordinate arrays
    lat = pd.Series(lat).interpolate().to_numpy()
    lon = pd.Series(lon).interpolate().to_numpy()
    depth = pd.Series(depth).interpolate().to_numpy()

    coords = {
        "time": time,
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
    trajectory = xr.Dataset(data_vars=data_vars, coords=coords)
    logger.success("trajectory dataset created successfully")
    return trajectory
