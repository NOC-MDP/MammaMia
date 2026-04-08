import uuid
from datetime import datetime

import numpy as np
import xarray as xr
from loguru import logger

from mamma_mia.find_worlds import FindWorlds

# TODO need to add cleaning (removing spurious nans)
# TODO Need to add behaviour generation


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


def create_mission(
    platform: xr.Dataset,
    trajectory: xr.Dataset,
    mission_name: str,
    summary: str,
    mission_time_step: int = 60,
    apply_obs_error: bool = True,
) -> xr.DataTree:
    # if platform uses NMEA coords convert them to lat lon for payload
    if platform.attrs["NMEA_coordinates"]:
        logger.info("Platform requires NMEA coordinate conversion")
        trajectory["longitude"] = xr.apply_ufunc(
            __convert_to_decimal, trajectory["longitude"], vectorize=True
        )
        trajectory["latitude"] = xr.apply_ufunc(
            __convert_to_decimal, trajectory["latitude"], vectorize=True
        )
        logger.info("Successfully converted from NMEA coordinates to decimal degrees")
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
    # combine all the bits into one datatree
    mission = xr.DataTree.from_dict(
        {
            "/": root,
            "platform": platform,
            "trajectory": trajectory,
            **{f"payload/{sensor_name}": ds for sensor_name, ds in payload.items()},
        }
    )
    logger.success(f"mission {mission_name} created successfully")
    return mission


def build_mission(catalog, mission):
    """
    build missions, this searches for relevant data, downloads and updates attributes as needed
    Args:
        cat: Initialised Cats object, this contains catalogs for all source data

    Returns:
        void: Mission object is now populated with world data ready to build interpolators for. Matched worlds
              and zarr store attributes are updated with the new values (what worlds match sensors and trajectory etc)

    """
    matched_worlds = FindWorlds()
    matched_worlds.search_worlds(
        cat=catalog,
        payload=mission["payload"],
        extent=mission.attrs["geospatial_attrs"],
        source="CMEMS",
    )
    # TODO add matched worlds attributes into mission attributes
    # TODO download world data to cache
    return mission
