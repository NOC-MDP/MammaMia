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
import xarray as xr
from loguru import logger

from mamma_mia.platforms_xr import platforms
from mamma_mia.sensors_xr import sensors


def create_platform(platform_type: str, add_sensors: list = [""]):
    attributes = None
    # check if platform is a valid type and assert if not
    assert platform_type in platforms, (
        f"Invalid platform: {platform_type!r}\n"
        f"Available platforms: {set(platforms.keys())}"
    )
    attributes = platforms[platform_type]
    # add an requested sensors
    for sensor in add_sensors:
        if sensor in sensors:
            attributes["sensors"][sensor] = sensors[sensor]
    # check to see if any sensors are unmatched and list if not
    # also if any unmatched list availble
    unmatched = set(add_sensors) - set(sensors.keys())
    assert not unmatched, (
        f"Unmatched sensors: {unmatched}\n"
        f"Available sensors: {set(sensors.keys()) - set(add_sensors)}"
    )
    platform = xr.Dataset(data_vars={"behaviour": []}, attrs=attributes)
    logger.success(
        f"Successfully created platform of type: {platform_type} with sensors {add_sensors}"
    )
    return platform
