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

from mamma_mia.sensors_xr import sensors


def create_platform(spec_file: str) -> xr.Dataset:
    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)

    spec = raw["specification"]

    attributes = spec["platform"]
    attributes["sensors"] = {}
    # add requested sensors
    for sensor_key, sensor_val in spec["sensors"].items():
        attributes["sensors"][sensor_key] = sensor_val

    platform = xr.Dataset(data_vars={"behaviour": []}, attrs=attributes)
    logger.success(f"Successfully created platform of type: {spec['platform']['type']}")
    return platform
