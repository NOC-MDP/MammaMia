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
from attrs import define, frozen
from cattr import unstructure
from loguru import logger

from mamma_mia.exceptions import CriticalParameterMissing, NoValidSource
from mamma_mia.sensors import create_sensor_class


@define
class NavigationKeys:
    """
    stores navigation variable keys for input trajectory datasets
    """

    latitude: list[str]
    longitude: list[str]
    depth: list[str]
    time: list[str]
    pitch: list[str]
    roll: list[str]
    yaw: list[str]

    @classmethod
    def from_datalogger(
        cls, datalogger: create_sensor_class(frozen_mode=True), platform_attrs
    ):
        nav_keys = {
            "latitude": None,
            "longitude": None,
            "depth": None,
            "time": None,
            # as the keys below are optional, they should not be None as this causes issues with exporting
            "pitch": "",
            "roll": "",
            "yaw": "",
        }

        for parameter_key, specification in datalogger.specification.items():
            combined_string = f"{specification['meta_data'].parameter_id} {specification['meta_data'].standard_name}".lower()
            ds_keys = cls.find_parameter_keys(
                parameter=parameter_key, platform_attrs=platform_attrs
            )

            for key, nav_name in nav_keys.items():
                if key in combined_string:
                    nav_keys[key] = ds_keys

        if (
            nav_keys["latitude"] is None
            or nav_keys["longitude"] is None
            or nav_keys["depth"] is None
            or nav_keys["time"] is None
        ):
            raise CriticalParameterMissing("missing critical navigation parameter")

        return cls(
            latitude=nav_keys["latitude"],
            longitude=nav_keys["longitude"],
            depth=nav_keys["depth"],
            time=nav_keys["time"],
            pitch=nav_keys["pitch"],
            roll=nav_keys["roll"],
            yaw=nav_keys["yaw"],
        )

    @staticmethod
    def find_parameter_keys(
        parameter: str, platform_attrs, instrument_type: str = "data_logger"
    ) -> list[str]:
        # TODO need to handle the case if sensor_key is None after iterating over sensor keys
        sensor_key = None
        for key in platform_attrs.sensors.keys():
            if platform_attrs.sensors[key].instrument_type == instrument_type:
                sensor_key = key
                break

        parameter_keys = (
            platform_attrs.sensors[sensor_key]
            .specification[parameter]["meta_data"]
            .source_names
        )

        return parameter_keys


@frozen
class Trajectory:
    latitude: np.ndarray
    longitude: np.ndarray
    depth: np.ndarray
    time: np.ndarray
    pitch: np.ndarray
    roll: np.ndarray
    yaw: np.ndarray

    @classmethod
    def for_glidersim(cls):
        logger.info("creating empty single point trajectory for glider sim")
        cls(
            latitude=np.array(-999.999),
            longitude=np.array(-999.999),
            depth=np.array(-999.999),
            time=np.array(-999.999),
            roll=np.array(-999.999),
            yaw=np.array(-999.999),
            pitch=np.array(-999.999),
        )

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, navigation_keys: NavigationKeys):
        """
        creates a trajectory from a dataframe
        Args:
            navigation_keys:
            df: pandas dataframe

        Returns:
            trajectory object

        """
        # go through navigation keys and find correct variable names
        vars_to_check = [
            x for xs in list(unstructure(navigation_keys).values()) for x in xs
        ]
        vars_to_check = [x for x in vars_to_check if x in df.columns]
        time_len = len(df)

        # valid mask (rows with no NaN in key variables)
        valid_mask = df[vars_to_check].notna().all(axis=1)
        df_clean = df.loc[valid_mask]
        clean_len = len(df_clean)
        clean_percent = clean_len / time_len

        if clean_percent < 0.75:
            logger.warning(
                "cleaned dataset less than 75% of original, will interpolate instead of clean"
            )
            # interpolate missing values for all non-time columns
            df_wo_time = df.drop(
                columns=[col for col in ["TIME", "TIME_GPS"] if col in df.columns]
            )
            df_interp = df_wo_time.interpolate(method="linear", limit_direction="both")
            # Add back time
            df_interp["TIME"] = df["TIME"]

            # remove rows that are still NaN in key vars
            valid_mask = df_interp[vars_to_check].notna().all(axis=1)
            df_clean = df_interp.loc[valid_mask]
        # convert to datetime
        df_clean["TIME"] = pd.to_datetime(df_clean["TIME"], format="%d/%m/%Y %H:%M:%S")
        # add data sources
        # TODO the add data sources used to find correct source key and filter NaNs which is now handled
        # TODO by the cleaning process above (the add source would only filter the specific source rather than whole dataset)
        # TODO therefore this is pretty redundant and needs refactoring
        latitude = cls.__add_source(ds=df_clean, source_keys=navigation_keys.latitude)
        longitude = cls.__add_source(ds=df_clean, source_keys=navigation_keys.longitude)
        depth = cls.__add_source(ds=df_clean, source_keys=navigation_keys.depth)
        time = cls.__add_source(ds=df_clean, source_keys=navigation_keys.time)

        if (
            latitude.size != depth.size
            or longitude.size != depth.size
            or latitude.size != longitude.size
        ):
            raise Exception(
                "NaN filtering resulted in different sized navigation parameters"
            )

        try:
            if navigation_keys.pitch is not None:
                pitch = cls.__add_source(ds=df_clean, source_keys=navigation_keys.pitch)
            else:
                logger.warning(f"Optional parameter pitch not specified in datalogger")
                pitch = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional pitch parameter for trajectory not found in simulated data: No variable named '{navigation_keys.pitch}'"
            )
            pitch = np.zeros_like(depth)

        try:
            if navigation_keys.yaw is not None:
                yaw = cls.__add_source(ds=df_clean, source_keys=navigation_keys.yaw)
            else:
                logger.warning(f"Optional parameter yaw not specified in datalogger")
                yaw = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional yaw parameter for trajectory not found in simulated data: No variable named '{navigation_keys.yaw}'"
            )
            yaw = np.zeros_like(depth)

        try:
            if navigation_keys.roll is not None:
                roll = cls.__add_source(ds=df_clean, source_keys=navigation_keys.roll)
            else:
                logger.warning(f"Optional parameter roll not specified in datalogger")
                roll = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional roll parameter for trajectory not found in simulated data: No variable named '{navigation_keys.roll}'"
            )
            roll = np.zeros_like(depth)

        return cls(
            latitude=np.array(latitude, dtype=np.float64),
            longitude=np.array(longitude, dtype=np.float64),
            depth=np.array(depth, dtype=np.float64),
            pitch=np.array(pitch, dtype=np.float64),
            roll=np.array(roll, dtype=np.float64),
            yaw=np.array(yaw, dtype=np.float64),
            time=np.array(time, dtype=np.datetime64),
        )

    @classmethod
    def from_xarray(cls, ds: xr.Dataset, navigation_keys: NavigationKeys):
        """
        Creates a trajectory from an xarray dataset
        Args:
            ds:
            navigation_keys:

        Returns:

        """
        # go through navigation keys and find correct variable names
        vars_to_check = [
            x for xs in list(unstructure(navigation_keys).values()) for x in xs
        ]
        time_dim = max(ds.dims, key=lambda d: ds.sizes[d])
        time_len = ds.sizes[time_dim]
        vars_to_check = [x for x in vars_to_check if x in ds.variables]
        # generate NaN mask
        valid_mask = np.logical_and.reduce([~ds[var].isnull() for var in vars_to_check])
        # clean dataset
        ds_clean = ds.isel({time_dim: valid_mask})
        clean_len = ds_clean.sizes[time_dim]
        clean_percent = clean_len / time_len
        if clean_percent < 0.75:
            logger.warning(
                "cleaned dataset less than 75% of original, will interpolate instead of clean"
            )
            time_var = ds["TIME"]
            ds_wo_time = ds.drop_vars("TIME")
            ds_wo_time = ds_wo_time.drop_vars("TIME_GPS")
            ds_clean = ds_wo_time.interpolate_na(dim=time_dim)
            ds_clean["TIME"] = time_var
            valid_mask = np.logical_and.reduce(
                [~ds_clean[var].isnull() for var in vars_to_check]
            )
            ds_clean = ds_clean.isel({time_dim: valid_mask})

        # add data sources
        # TODO the add data sources used to find correct source key and filter NaNs which is now handled
        # TODO by the cleaning process above (the add source would only filter the specific source rather than whole dataset)
        # TODO therefore this is pretty redundant and needs refactoring
        latitude = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.latitude)
        longitude = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.longitude)
        depth = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.depth)
        time = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.time)

        if (
            latitude.size != depth.size
            or longitude.size != depth.size
            or latitude.size != longitude.size
        ):
            raise Exception(
                "NaN filtering resulted in different sized navigation parameters"
            )

        try:
            if navigation_keys.pitch is not None:
                pitch = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.pitch)
            else:
                logger.warning(f"Optional parameter pitch not specified in datalogger")
                pitch = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional pitch parameter for trajectory not found in simulated data: No variable named '{navigation_keys.pitch}'"
            )
            pitch = np.zeros_like(depth)

        try:
            if navigation_keys.yaw is not None:
                yaw = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.yaw)
            else:
                logger.warning(f"Optional parameter yaw not specified in datalogger")
                yaw = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional yaw parameter for trajectory not found in simulated data: No variable named '{navigation_keys.yaw}'"
            )
            yaw = np.zeros_like(depth)

        try:
            if navigation_keys.roll is not None:
                roll = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.roll)
            else:
                logger.warning(f"Optional parameter roll not specified in datalogger")
                roll = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional roll parameter for trajectory not found in simulated data: No variable named '{navigation_keys.roll}'"
            )
            roll = np.zeros_like(depth)

        return cls(
            latitude=np.array(latitude, dtype=np.float64),
            longitude=np.array(longitude, dtype=np.float64),
            depth=np.array(depth, dtype=np.float64),
            pitch=np.array(pitch, dtype=np.float64),
            roll=np.array(roll, dtype=np.float64),
            yaw=np.array(yaw, dtype=np.float64),
            time=np.array(time, dtype=np.datetime64),
        )

    @staticmethod
    def __add_source(ds: xr.Dataset | pd.DataFrame, source_keys: list[str]):
        """
        tries each source key and returns first matching source dataset
        Args:
            ds:
            source_keys:

        Returns:
            input dataset variable
        """
        source = None
        for key in source_keys:
            try:
                source = ds[key]  # [~np.isnan(ds[key])]
                break
            except KeyError:
                pass
        if source is None:
            raise NoValidSource
        return source
