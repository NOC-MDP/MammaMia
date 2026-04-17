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
import uuid
from datetime import datetime

import gsw
import numpy as np
import xarray as xr
from loguru import logger

from mamma_mia.sim_error_xr import simulate_sensor_error


def create_mission(
    platform: xr.Dataset,
    trajectory: xr.Dataset,
    mission_name: str,
    summary: str,
    mission_time_step: int = 60,
    apply_obs_error: bool = True,
) -> xr.DataTree:
    logger.info(f"creating a mission datatree called {mission_name}")
    # if platform uses NMEA coords convert them to lat lon for payload
    if platform.attrs["NMEA_coordinates"]:
        logger.info("Platform requires NMEA coordinate conversion")
        trajectory["longitude"] = xr.apply_ufunc(
            __convert_to_decimal, trajectory["longitude"], vectorize=True
        )
        trajectory["latitude"] = xr.apply_ufunc(
            __convert_to_decimal, trajectory["latitude"], vectorize=True
        )
        logger.success(
            "Successfully converted from NMEA coordinates to decimal degrees"
        )
    # write geospatial attributes to allow world search
    geospatial_attrs = {
        "geospatial_bounds_crs": "EPSG:4326",
        "geospatial_bounds_vertical_crs": "EPSG:5831",
        "geospatial_lat_max": float(trajectory.latitude.max()),
        "geospatial_lat_min": float(trajectory.latitude.min()),
        "geospatial_lat_units": "degrees",
        "geospatial_lon_max": float(trajectory.longitude.max()),
        "geospatial_lon_min": float(trajectory.longitude.min()),
        "geospatial_lon_units": "degrees",
        "geospatial_vertical_max": float(trajectory.depth.max()),
        "geospatial_vertical_min": float(trajectory.depth.min()),
        "geospatial_vertical_units": "m",
        "Westernmost_Easting": float(trajectory.longitude.min()),
        "Easternmost_Easting": float(trajectory.longitude.max()),
        "Northernmost_Northing": float(trajectory.latitude.max()),
        "Southernmost_Northing": float(trajectory.latitude.min()),
        "geospatial_bounds": (
            f"POLYGON(({np.min(trajectory.longitude).values},"
            f"{np.max(trajectory.longitude).values},"
            f"{np.min(trajectory.latitude).values},"
            f"{np.max(trajectory.latitude).values},))"
        ),
        "time_coverage_end": str(np.datetime_as_string(trajectory.time[-1], unit="s")),
        "time_coverage_start": str(np.datetime_as_string(trajectory.time[0], unit="s")),
        "featureType": "Trajectory",
    }

    mission_attrs = {
        "name": mission_name,
        "uuid": str(uuid.uuid4()),
        "date_created": datetime.strftime(datetime.now(), format="YYYY/MM/DDTHH:MM:SS"),
        "summary": summary,
        "mission_time_step": mission_time_step,
        "apply_obs_error": apply_obs_error,
    }

    root = xr.Dataset(
        attrs={
            "geospatial_attrs": geospatial_attrs,
            "mission_attrs": mission_attrs,
        }
    )
    logger.success(
        "successfully created root dataset with mission and geospatial attributes"
    )
    t_start = trajectory.time.values[0]
    t_end = trajectory.time.values[-1]
    # create new payload time coords to interpolate trajectory onto
    new_time = np.arange(
        t_start,
        t_end + np.timedelta64(mission_attrs["mission_time_step"], "s"),
        np.timedelta64(mission_attrs["mission_time_step"], "s"),
        dtype="datetime64[ns]",
    )

    # interpolate trajectory coords onto new time axis
    traj_interp = trajectory.interp(time=new_time, method="linear")

    n_times = len(new_time)
    # create new coords for payload dataset
    coords = {
        "time": new_time,
        "latitude": ("time", traj_interp.latitude.values),
        "longitude": ("time", traj_interp.longitude.values),
        "depth": ("time", traj_interp.depth.values),
    }
    logger.success(
        "successfully interpolated trajectory to match specified mission timestep"
    )
    # create payload dataset, an dataset for each sensor with variables stored as empty arrays
    payload = {
        sensor_name: xr.Dataset(
            coords=coords,
            data_vars={
                param: ("time", np.full(n_times, np.nan))
                for param in sensor_params.keys()
            },
        )
        for sensor_name, sensor_params in platform.attrs["sensors"].items()
    }
    logger.success("successfully built payload dataset")
    # Define state mapping (CF convention)
    state_map = {"hovering": 0, "diving": 1, "climbing": 2, "surfaced": 3}

    # Calculate changes in depth to determine platform behaviour
    dz = np.gradient(traj_interp.depth)

    # Build integer state array, defaulting to hovering
    state = np.zeros(len(traj_interp.depth), dtype=np.int8)
    state[dz > platform.attrs["descent_thresh"]] = state_map["diving"]
    state[dz < platform.attrs["ascent_thresh"]] = state_map["climbing"]

    surfaced_mask = (traj_interp.depth[:] < platform.attrs["near_surface_thresh"]) & (
        np.abs(dz) < platform.attrs["ascent_thresh"]
    )
    state[surfaced_mask] = state_map["surfaced"]

    platform["state"] = xr.DataArray(
        state,
        dims=["time"],
        attrs={
            "long_name": "platform behaviour state",
            "state_meanings": state_map,
        },
    )
    logger.success("successfully determined and created platform state")
    # combine all the bits into one datatree
    mission = xr.DataTree.from_dict(
        {
            "/": root,
            "platform": platform,
            "trajectory": trajectory,
            **{f"payload/{sensor_name}": ds for sensor_name, ds in payload.items()},
        }
    )
    logger.success(f"mission {mission_name} datatree created successfully")
    return mission


def fly(mission: xr.DataTree, interpolators) -> xr.DataTree:
    """ """
    logger.info(
        f"flying {mission.attrs['mission_attrs']['name']} using {mission['platform'].attrs['type']}"
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
            if mission.attrs["mission_attrs"]["apply_obs_error"]:
                logger.info(
                    f"apply simulated observation errors set to True, applying to {variable_key} now"
                )
                result = simulate_sensor_error(
                    model_t=result,
                    mission_ts=mission.attrs["mission_attrs"]["mission_time_step"],
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

    logger.success(f"{mission.attrs['mission_attrs']['name']} flown successfully")
    return mission


def __update_node(node, result, variable_key):
    # Grab the existing DataArray to preserve coords/dims/attrs
    existing_da = node.ds[variable_key]
    # Create a new DataArray with the updated values (same coords/dims)
    new_da = existing_da.copy(data=result)
    # Update the node's dataset in-place
    node.update({variable_key: new_da})


# From: https://github.com/smerckel/latlon/blob/main/latlon/latlon.py
# Lucas Merckelbach
def __convert_to_decimal(x):
    """
    Converts a latitude or longitude in NMEA format to decimal degrees
    """
    sign = np.sign(x)
    x_abs = np.abs(x)
    degrees = np.floor(x_abs / 100.0)
    minutes = x_abs - degrees * 100
    decimal_format = degrees + minutes / 60.0
    return decimal_format * sign
