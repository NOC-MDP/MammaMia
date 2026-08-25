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

import xarray as xr
from loguru import logger


def create_platform(spec_file: str) -> xr.Dataset:
    """
    Create a platform Dataset from a TOML specification file.

    Parameters
    ----------
    spec_file : str
        Path to the platform specification file, which defines platform-level
        attributes (e.g. name, type) and the sensor suite configuration
        (e.g. sensor models, observation error parameters).

    Returns
    -------
    xr.Dataset
        A Dataset encoding the platform attributes and sensor specifications,
        suitable for passing to `create_mission`.
    """
    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]
    # add platform attribures
    attributes = spec["platform"]
    # add sensors
    attributes["sensors"] = spec["sensors"]
    # create platform dataset with empty state array to be filled when creating mission
    platform = xr.Dataset(data_vars={"state": []}, attrs=attributes)
    logger.success(f"Successfully created platform of type: {spec['platform']['type']}")
    return platform
