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

import gsw
import xarray as xr
from loguru import logger

from mamma_mia.sim_error import simulate_sensor_error


@overload
def fly(mission: xr.DataTree, interpolators: dict) -> xr.DataTree: ...


@overload
def fly(mission: list[xr.DataTree], interpolators: list[dict]) -> list[xr.DataTree]: ...


def fly(
    mission: Union[xr.DataTree, list[xr.DataTree]],
    interpolators: Union[dict, list[dict]],
) -> Union[xr.DataTree, list[xr.DataTree]]:
    if isinstance(mission, list) and isinstance(interpolators, list):
        return [_fly(m, i) for m, i in zip(mission, interpolators)]
    elif isinstance(interpolators, dict) and isinstance(mission, xr.DataTree):
        return _fly(mission=mission, interpolators=interpolators)
    else:
        raise Exception("unsupported mission or interpolator type")


def _fly(mission: xr.DataTree, interpolators: dict) -> xr.DataTree:
    """
    Fly a mission by interpolating sensor payloads along the payload coordinates.

    Parameters
    ----------
    mission : xr.DataTree
        A mission DataTree as returned by `create_mission`, containing platform,
        trajectory, and payload nodes with the mission time grid.
    interpolators :
        Collection of interpolator objects used to sample geophysical fields at
        the payload coordinates for each sensor.

    Returns
    -------
    xr.DataTree
        The input mission DataTree with the payload node populated with
        interpolated sensor observations sampled along the mission time grid.
    """
    logger.info(
        f"flying {mission.attrs['name']} using {mission['platform'].attrs['type']}"
    )
    for sensor_key, sensor in mission.payload.items():
        for variable_key in sensor.keys():
            flight = {
                "longitude": mission.payload[sensor_key][variable_key].longitude.values,
                "latitude": mission.payload[sensor_key][variable_key].latitude.values,
                "depth": mission.payload[sensor_key][variable_key].depth.values,
                "time": mission.payload[sensor_key][variable_key].time.values,
            }
            try:
                result = interpolators[variable_key].quadrivariate(flight)
            except KeyError:
                logger.warning(
                    f"no interpolator found for variable {variable_key} in sensor {sensor_key}"
                )
                # pressure is special case as it can be derived from depth coordinates and latitude
                if variable_key == "pressure":
                    logger.info(
                        "missing interpolator is pressure, will convert from depths coords"
                    )
                    result = gsw.p_from_z(
                        z=-1 * mission.payload[sensor_key][variable_key].depth.values,
                        lat=mission.payload[sensor_key][variable_key].latitude.values,
                    )
                else:
                    continue
            if mission.attrs["apply_obs_error"]:
                logger.info(
                    f"apply simulated observation errors set to True, applying to {variable_key} now"
                )
                result = simulate_sensor_error(
                    model_t=result,
                    mission_ts=mission.attrs["mission_time_step"],
                    accuracy_bias=mission.platform.attrs["sensors"][sensor_key][
                        variable_key
                    ]["accuracy"],
                    noise_std=mission.platform.attrs["sensors"][sensor_key][
                        variable_key
                    ]["noise_std"],
                    resolution=mission.platform.attrs["sensors"][sensor_key][
                        variable_key
                    ]["resolution"],
                    drift_per_month=mission.platform.attrs["sensors"][sensor_key][
                        variable_key
                    ]["drift_per_month"],
                    m_min=mission.platform.attrs["sensors"][sensor_key][variable_key][
                        "range"
                    ][0],
                    m_max=mission.platform.attrs["sensors"][sensor_key][variable_key][
                        "range"
                    ][1],
                    percent_errors=mission.platform.attrs["sensors"][sensor_key][
                        variable_key
                    ]["percent_errors"],
                )

            # Get the node you want to update
            node = mission.payload[sensor_key]
            __update_node(node, result, variable_key)

    logger.success(f"{mission.attrs['name']} flown successfully")
    return mission


def __update_node(node, result, variable_key):
    # Grab the existing DataArray to preserve coords/dims/attrs
    existing_da = node.ds[variable_key]
    # Create a new DataArray with the updated values (same coords/dims)
    new_da = existing_da.copy(data=result)
    # Update the node's dataset in-place
    node.update({variable_key: new_da})
