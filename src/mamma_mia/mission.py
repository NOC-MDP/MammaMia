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

import os
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import xarray as xr
from attrs import define, frozen
from cattr import unstructure
from mamma_mia import Platform, create_platform_attrs
from mamma_mia import create_sensor_class
import uuid
from loguru import logger
import zarr
from mamma_mia.catalog import Cats
from mamma_mia.interpolator import Interpolators
from mamma_mia.worlds import SourceConfig
from mamma_mia.find_worlds import FindWorlds
from mamma_mia.get_worlds import get_worlds
from mamma_mia.exceptions import CriticalParameterMissing,NoValidSource
from scipy.interpolate import interp1d
from mamma_mia.gsw_funcs import ConvertedTSP, ConvertedP
from mamma_mia.worlds import WorldsConf, WorldExtent, WorldsAttributes
from mamma_mia.sim_error import simulate_sensor_error

@frozen
class Publisher:
    """
    stores details of mission publisher
    Args:
        email :str
        institution :str
        name :str
        type :str
        url :str
    """
    email: str = "mm1@mm.ac.uk"
    institution: str = "mamma-mia"
    name: str = "mm"
    type: str = ""
    url: str = "https://www.mm.ac.uk/"


@frozen
class Contributor:
    """
    stores details of mission contributor
    """
    email: str = "mm2@mm.ac.uk"
    name: str = "mm2"
    role: str = "Principal Investigator"
    role_vocab: str = ""


@frozen
class Creator:
    """
    stores details of mission creator
    Args:
        email:
        institution:
        name:
        creator_type:
        url:
    """
    email: str = "gliders@mm.ac.uk"
    institution: str = "MammaMia"
    name: str = "mamma mia"
    creator_type: str = ""
    url: str = "https://gliders.mm.ac.uk/"

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
    def from_datalogger(cls, datalogger: create_sensor_class(frozen_mode=True), platform_attrs):
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
            ds_keys = cls.find_parameter_keys(parameter=parameter_key, platform_attrs=platform_attrs)

            for key, nav_name in nav_keys.items():
                if key in combined_string:
                    nav_keys[key] = ds_keys

        if nav_keys["latitude"] is None or nav_keys["longitude"] is None or nav_keys["depth"] is None or nav_keys["time"] is None:
            raise CriticalParameterMissing("missing critical navigation parameter")

        return cls(latitude=nav_keys["latitude"],
                   longitude=nav_keys["longitude"],
                   depth=nav_keys["depth"],
                   time=nav_keys["time"],
                   pitch=nav_keys["pitch"],
                   roll=nav_keys["roll"],
                   yaw=nav_keys["yaw"]
                   )

    @staticmethod
    def find_parameter_keys(parameter: str, platform_attrs, instrument_type: str = "data_logger") -> list[str]:
        # TODO need to handle the case if sensor_key is None after iterating over sensor keys
        sensor_key = None
        for key in platform_attrs.sensors.keys():
            if platform_attrs.sensors[key].instrument_type == instrument_type:
                sensor_key = key
                break

        parameter_keys = platform_attrs.sensors[sensor_key].specification[parameter]["meta_data"].source_names

        return parameter_keys


@frozen
class MissionAttributes:
    mission: str
    internal_mission_identifier: str
    date_created: str
    summary: str
    title: str
    trajectory_path: str
    instruments:list[str]
    crs: str
    vertical_crs: str
    creator: Creator
    publisher: Publisher
    contributor: Contributor
    standard_name_vocabulary: str
    source_config: SourceConfig
    mission_time_step: int
    apply_obs_error: bool


@frozen
class GeospatialAttributes:
    geospatial_bounds_crs: str
    geospatial_bounds_vertical_crs: str

    geospatial_lat_max: np.float64
    geospatial_lat_min: np.float64
    geospatial_lat_units: str

    geospatial_lon_min: np.float64
    geospatial_lon_max: np.float64
    geospatial_lon_units: str

    geospatial_vertical_max: np.float64
    geospatial_vertical_min: np.float64
    geospatial_vertical_units: str

    Westernmost_Easting: np.float64
    Easternmost_Easting: np.float64
    Northernmost_Northing: np.float64
    Southernmost_Northing: np.float64

    geospatial_bounds: str

    time_coverage_start: str
    time_coverage_end: str
    featureType: str

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
        cls(latitude=np.array(-999.999),
            longitude=np.array(-999.999),
            depth=np.array(-999.999),
            time=np.array(-999.999),
            roll=np.array(-999.999),
            yaw=np.array(-999.999),
            pitch=np.array(-999.999),)

    @classmethod
    def from_dataframe(cls,df: pd.DataFrame,navigation_keys:NavigationKeys):
        """
        creates a trajectory from a dataframe
        Args:
            navigation_keys:
            df: pandas dataframe

        Returns:
            trajectory object

        """
        # go through navigation keys and find correct variable names
        vars_to_check =  [x for xs in list(unstructure(navigation_keys).values()) for x in xs]
        vars_to_check = [x for x in vars_to_check if x in df.columns]
        time_len = len(df)

        # valid mask (rows with no NaN in key variables)
        valid_mask = df[vars_to_check].notna().all(axis=1)
        df_clean = df.loc[valid_mask]
        clean_len = len(df_clean)
        clean_percent = clean_len / time_len

        if clean_percent < 0.75:
            logger.warning("cleaned dataset less than 75% of original, will interpolate instead of clean")
            # interpolate missing values for all non-time columns
            df_wo_time = df.drop(columns=[col for col in ["TIME", "TIME_GPS"] if col in df.columns])
            df_interp = df_wo_time.interpolate(method="linear", limit_direction="both")
            # Add back time
            df_interp["TIME"] = df["TIME"]

            # remove rows that are still NaN in key vars
            valid_mask = df_interp[vars_to_check].notna().all(axis=1)
            df_clean = df_interp.loc[valid_mask]
        # convert to datetime
        df_clean['TIME'] = pd.to_datetime(df_clean['TIME'], format='%d/%m/%Y %H:%M:%S')
        # add data sources
        # TODO the add data sources used to find correct source key and filter NaNs which is now handled
        # TODO by the cleaning process above (the add source would only filter the specific source rather than whole dataset)
        # TODO therefore this is pretty redundant and needs refactoring
        latitude = cls.__add_source(ds=df_clean, source_keys=navigation_keys.latitude)
        longitude =cls.__add_source(ds=df_clean, source_keys=navigation_keys.longitude)
        depth = cls.__add_source(ds=df_clean, source_keys=navigation_keys.depth)
        time = cls.__add_source(ds=df_clean, source_keys=navigation_keys.time)

        if latitude.size != depth.size or longitude.size != depth.size or latitude.size != longitude.size:
            raise Exception("NaN filtering resulted in different sized navigation parameters")

        try:
            if navigation_keys.pitch is not None:
                pitch = cls.__add_source(ds=df_clean, source_keys=navigation_keys.pitch)
            else:
                logger.warning(f"Optional parameter pitch not specified in datalogger")
                pitch = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional pitch parameter for trajectory not found in simulated data: No variable named '{navigation_keys.pitch}'")
            pitch = np.zeros_like(depth)

        try:
            if navigation_keys.yaw is not None:
                yaw = cls.__add_source(ds=df_clean, source_keys=navigation_keys.yaw)
            else:
                logger.warning(f"Optional parameter yaw not specified in datalogger")
                yaw = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional yaw parameter for trajectory not found in simulated data: No variable named '{navigation_keys.yaw}'")
            yaw = np.zeros_like(depth)

        try:
            if navigation_keys.roll is not None:
                roll = cls.__add_source(ds=df_clean, source_keys=navigation_keys.roll)
            else:
                logger.warning(f"Optional parameter roll not specified in datalogger")
                roll = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional roll parameter for trajectory not found in simulated data: No variable named '{navigation_keys.roll}'")
            roll = np.zeros_like(depth)

        return cls(latitude=np.array(latitude, dtype=np.float64),
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
        vars_to_check =  [x for xs in list(unstructure(navigation_keys).values()) for x in xs]
        time_dim = max(ds.dims,key=lambda d: ds.sizes[d])
        time_len = ds.sizes[time_dim]
        vars_to_check = [x for x in vars_to_check if x in ds.variables]
        # generate NaN mask
        valid_mask = np.logical_and.reduce([~ds[var].isnull() for var in vars_to_check])
        # clean dataset
        ds_clean = ds.isel({time_dim: valid_mask})
        clean_len = ds_clean.sizes[time_dim]
        clean_percent = clean_len / time_len
        if clean_percent < 0.75:
            logger.warning("cleaned dataset less than 75% of original, will interpolate instead of clean")
            time_var = ds["TIME"]
            ds_wo_time = ds.drop_vars('TIME')
            ds_wo_time = ds_wo_time.drop_vars('TIME_GPS')
            ds_clean = ds_wo_time.interpolate_na(dim=time_dim)
            ds_clean["TIME"] = time_var
            valid_mask = np.logical_and.reduce([~ds_clean[var].isnull() for var in vars_to_check])
            ds_clean = ds_clean.isel({time_dim: valid_mask})

        # add data sources
        # TODO the add data sources used to find correct source key and filter NaNs which is now handled
        # TODO by the cleaning process above (the add source would only filter the specific source rather than whole dataset)
        # TODO therefore this is pretty redundant and needs refactoring
        latitude = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.latitude)
        longitude =cls.__add_source(ds=ds_clean, source_keys=navigation_keys.longitude)
        depth = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.depth)
        time = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.time)

        if latitude.size != depth.size or longitude.size != depth.size or latitude.size != longitude.size:
            raise Exception("NaN filtering resulted in different sized navigation parameters")

        try:
            if navigation_keys.pitch is not None:
                pitch = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.pitch)
            else:
                logger.warning(f"Optional parameter pitch not specified in datalogger")
                pitch = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional pitch parameter for trajectory not found in simulated data: No variable named '{navigation_keys.pitch}'")
            pitch = np.zeros_like(depth)

        try:
            if navigation_keys.yaw is not None:
                yaw = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.yaw)
            else:
                logger.warning(f"Optional parameter yaw not specified in datalogger")
                yaw = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional yaw parameter for trajectory not found in simulated data: No variable named '{navigation_keys.yaw}'")
            yaw = np.zeros_like(depth)

        try:
            if navigation_keys.roll is not None:
                roll = cls.__add_source(ds=ds_clean, source_keys=navigation_keys.roll)
            else:
                logger.warning(f"Optional parameter roll not specified in datalogger")
                roll = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional roll parameter for trajectory not found in simulated data: No variable named '{navigation_keys.roll}'")
            roll = np.zeros_like(depth)



        return cls(latitude=np.array(latitude, dtype=np.float64),
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
                source = ds[key]#[~np.isnan(ds[key])]
                break
            except KeyError:
                pass
        if source is None:
            raise NoValidSource
        return source




@define
class Mission:
    platform: Platform
    attrs: MissionAttributes
    geospatial_attrs: GeospatialAttributes
    navigation_keys: NavigationKeys
    payload: dict[str, np.ndarray]
    worlds: WorldsConf
    trajectory: Trajectory

    @classmethod
    def for_campaign(cls,
                      mission: str,
                      summary: str,
                      title: str,
                      platform_attributes: create_platform_attrs(),
                      trajectory_path: str,
                      source_config: SourceConfig,
                      excess_space: int,
                      extra_depth: int,
                      msm_priority: int,
                      cmems_priority: int,
                      crs: str,
                      vertical_crs: str,
                      creator: Creator,
                      publisher: Publisher,
                      contributor: Contributor,
                      standard_name_vocabulary,
                      mission_time_step: int,
                      apply_obs_error: bool,
                      ):
        platform = Platform(attrs=platform_attributes,behaviour=np.empty((0,)))
        instruments = []
        for instrument in platform.attrs.sensors.values():
            instruments.append(instrument.sensor_name)

        attrs = MissionAttributes(mission=mission,
                                      summary=summary,
                                      title=title,
                                      creator=creator,
                                      publisher=publisher,
                                      contributor=contributor,
                                      trajectory_path=trajectory_path,
                                      date_created=datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S.%f"),
                                      internal_mission_identifier=str(uuid.uuid4()),
                                      instruments=instruments,
                                      crs=crs,
                                      vertical_crs=vertical_crs,
                                      standard_name_vocabulary=standard_name_vocabulary,
                                      source_config=source_config,
                                      mission_time_step=mission_time_step,
                                      apply_obs_error=apply_obs_error
                                      )

        # find datalogger
        data_logger_key = None
        for sensor_key, sensor in platform.attrs.sensors.items():
            if sensor.instrument_type == "data_logger":
                data_logger_key = sensor_key
        if data_logger_key is None:
            raise Exception("No data logger found for this platform")

        # generate variable keys for navigation/trajectory variables in input dataset
        nav_keys = NavigationKeys.from_datalogger(datalogger=platform.attrs.sensors[data_logger_key],platform_attrs=platform.attrs)

        # generate trajectory
        if attrs.trajectory_path[-3:] == ".nc":
            ds = xr.open_dataset(attrs.trajectory_path)
            trajectory = Trajectory.from_xarray(ds=ds, navigation_keys=nav_keys)
        elif attrs.trajectory_path[-4:] == ".csv":
            df = pd.read_csv(attrs.trajectory_path)
            trajectory = Trajectory.from_dataframe(df=df, navigation_keys=nav_keys)
        else:
            raise Exception(f"trajectory file type: {attrs.trajectory_path[-3:]} is not supported")


        #seconds_into_flight = (trajectory.time - trajectory.time[0]) / np.timedelta64(1, 's')
        # calculate changes in depth to determine platform behaviour
        dz = np.gradient(trajectory.depth)
        # TODO set these dynamically based on the platform
        ascent_thresh = 0.05  # m/s, adjust based on your system
        descent_thresh = -0.05  # m/s
        near_surface_thresh = 1
        # Using dz and set thresholds, create an event graph for the platform
        event = np.full_like(trajectory.depth, 'hovering', dtype="S8")
        # Diving: dz < descent_thresh
        event[dz > descent_thresh] = 'diving'
        # Climbing: dz > ascent_thresh
        event[dz < ascent_thresh] = 'climbing'
        # Surfaced / Near surface: depth < threshold and nearly zero vertical speed
        surfaced_mask = (trajectory.depth[:] < near_surface_thresh) & (np.abs(dz) < ascent_thresh)
        event[surfaced_mask] = 'surfaced'
        platform.behaviour = np.array(event, dtype="S8")

        if platform.attrs.NEMA_coordinate_conversion:
            logger.info(f"Platform requires NEMA coordinate conversion")
            for i in range(trajectory.longitude.__len__()):
                trajectory.longitude[i] = cls.__convert_to_decimal(trajectory.longitude[i])
            for i in range(trajectory.latitude.__len__()):
                trajectory.latitude[i] = cls.__convert_to_decimal(trajectory.latitude[i])
            logger.info(f"Successfully converted from NEMA coordinates to decimal degrees")

        geospatial_attrs = GeospatialAttributes(
            geospatial_bounds_crs=crs,
            geospatial_bounds_vertical_crs=vertical_crs,
            geospatial_lat_max=np.max(trajectory.latitude),
            geospatial_lat_min=np.min(trajectory.latitude),
            geospatial_lat_units=cls.get_parameter_units(platform_attrs=platform.attrs ,parameter="latitude"),
            geospatial_lon_max=np.max(trajectory.longitude),
            geospatial_lon_min=np.min(trajectory.longitude),
            geospatial_lon_units=cls.get_parameter_units(platform_attrs=platform.attrs,parameter="longitude"),
            geospatial_vertical_max= np.max(trajectory.depth),
            geospatial_vertical_min= np.min(trajectory.depth),
            geospatial_vertical_units="m",
            Westernmost_Easting=np.min(trajectory.longitude),
            Easternmost_Easting=np.max(trajectory.longitude),
            Northernmost_Northing=np.max(trajectory.latitude),
            Southernmost_Northing=np.min(trajectory.latitude),
            geospatial_bounds=(f"POLYGON(({np.min(trajectory.longitude)},"
                                           f"{np.max(trajectory.longitude)},"
                                           f"{np.min(trajectory.latitude)},"
                                           f"{np.max(trajectory.latitude)},))"),
            time_coverage_end=str(np.datetime_as_string(trajectory.time[-1], unit="s")),
            time_coverage_start=str(np.datetime_as_string(trajectory.time[0], unit="s")),
            featureType="Trajectory"
        )

        extent = WorldExtent(
            lat_max=np.around(np.nanmax(trajectory.latitude), 2) + excess_space,
            lat_min=np.around(np.nanmin(trajectory.latitude), 2) - excess_space,
            lon_max=np.around(np.nanmax(trajectory.longitude), 2) + excess_space,
            lon_min=np.around(np.nanmin(trajectory.longitude), 2) - excess_space,
            time_start=str(np.datetime_as_string(trajectory.time[0] - np.timedelta64(30, 'D'), unit="D")),
            time_end=str(np.datetime_as_string(trajectory.time[-1] + np.timedelta64(30, 'D'), unit="D")),
            depth_max=np.around(np.nanmax(trajectory.depth), 2) + extra_depth,
        )
        worlds = WorldsConf(
            attributes=WorldsAttributes(extent=extent,
                                                 catalog_priorities={"msm": msm_priority, "cmems": cmems_priority,"local":3},
                                                 matched_worlds={},
                                                 interpolator_priorities={}
                                                 ),
            worlds={},
            stores={}
        )
        payload = {}
        # total mission time in seconds (largest that a payload array could be)
        mission_total_time_seconds = (trajectory.time[-1] - trajectory.time[0]).astype('timedelta64[s]')
        mission_total_time_steps = np.ceil(mission_total_time_seconds.astype(int) / mission_time_step).astype(int)
        for name, sensor in platform.attrs.sensors.items():
            for name2, specification in sensor.specification.items():
                payload[name2] = np.empty(shape=mission_total_time_steps, dtype=np.float64)
        return cls(platform=platform,
                   attrs=attrs,
                   geospatial_attrs=geospatial_attrs,
                   navigation_keys=nav_keys,
                   payload=payload,
                   worlds=worlds,
                   trajectory=trajectory
                   )

    # From: https://github.com/smerckel/latlon/blob/main/latlon/latlon.py
    # Lucas Merckelbach
    @staticmethod
    def __convert_to_decimal(x):
        """
        Converts a latitude or longitude in NMEA format to decimal degrees
        """
        sign = np.sign(x)
        x_abs = np.abs(x)
        degrees = np.floor(x_abs / 100.)
        minutes = x_abs - degrees * 100
        decimal_format = degrees + minutes / 60.
        return decimal_format * sign

    @staticmethod
    def get_parameter_units(platform_attrs,parameter: str, instrument_type: str = "data_logger") -> str:
        sensor_key = None
        parameter_units = None
        for key in platform_attrs.sensors.keys():
            if platform_attrs.sensors[key].instrument_type == instrument_type:
                sensor_key = key
                break
        try:
            parameter_units = platform_attrs.sensors[sensor_key].specification[parameter]["meta_data"].unit_of_measure
        except KeyError:
            for val in platform_attrs.sensors[sensor_key].specification.values():
                try:
                    if parameter in val["meta_data"].parameter_definition.lower():
                        parameter_units = val["meta_data"].unit_of_measure
                except AttributeError:
                    if parameter in val["meta_data"].long_name.lower():
                        parameter_units = val["meta_data"].units

        return parameter_units

    def build_mission(self, cat: Cats):
        """
        build missions, this searches for relevant data, downloads and updates attributes as needed
        Args:
            cat: Initialised Cats object, this contains catalogs for all source data

        Returns:
            void: Mission object is now populated with world data ready to build interpolators for. Matched worlds
                  and zarr store attributes are updated with the new values (what worlds match sensors and trajectory etc)

        """
        matched_worlds = FindWorlds()
        matched_worlds.search_worlds(cat=cat, payload=self.payload, extent=self.worlds.attributes.extent,source=self.attrs.source_config)
        self.worlds.attributes.matched_worlds = matched_worlds.entries
        data_stores = get_worlds(cat=cat, worlds=self.worlds,source=self.attrs.source_config)
        self.worlds.stores = data_stores

    def fly(self, interpolator: Interpolators):
        """

        Args:

            interpolator: Interpolator object with interpolators to fly through

        Returns:
            void: mission object with filled reality arrays of interpolated data, i.e. AUV has flown its
                  mission through the world.
        """
        logger.info(f"flying {self.attrs.mission} using {self.platform.attrs.entity_name}")
        # build orientation arrays, if missing from trajectory replace with zeros
        try:
            pitch = np.array(self.trajectory.pitch)
        except AttributeError:
            pitch = np.zeros(shape=self.trajectory.latitude.__len__())
        try:
            yaw = np.array(self.trajectory.yaw)
        except AttributeError:
            yaw = np.zeros(shape=self.trajectory.latitude.__len__())
        try:
            roll = np.array(self.trajectory.roll)
        except AttributeError:
            roll = np.zeros(shape=self.trajectory.latitude.__len__())
        flight = {
            "longitude": np.array(self.trajectory.longitude),
            "latitude": np.array(self.trajectory.latitude),
            "depth": np.array(self.trajectory.depth),
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "time": np.array(self.trajectory.time, dtype='datetime64'),
        }

        resampled_flight = self._resample_flight(flight=flight, new_interval_seconds=self.attrs.mission_time_step)
        # subset flight to only what is needed for interpolation (position rather than orientation)
        flight_subset = {key: resampled_flight[key] for key in ["longitude", "latitude", "depth", "time"]}
        navigation_alias = {}
        # get navigation keys and any aliases that relate to them
        for k1, v1 in self.platform.attrs.sensors.items():
            if self.platform.attrs.sensors[k1].instrument_type == "data_logger":
                navigation_keys = list(self.platform.attrs.sensors[k1].specification.keys())
                for k2, parameter in self.platform.attrs.sensors[k1].specification.items():
                    for nav_key in navigation_keys:
                        if nav_key == parameter["meta_data"].parameter_id:
                            navigation_alias[nav_key] = parameter["meta_data"].alternate_labels
        marked_keys = []
        for key in self.payload.keys():
            try:
                logger.info(f"flying through {key} world and creating interpolated data for flight")
                track = interpolator.interpolator[key].quadrivariate(flight_subset)
            except KeyError:
                track = None
                # pressure is kind of a special case as its not found in the models and is derived from trajectory depth
                if key == "PRESSURE":
                    logger.info(f"converting depth data into pressure data")
                    # create pressure from depths and latitudes
                    track = ConvertedP.d_2_p(depth=resampled_flight["depth"],latitude=resampled_flight["latitude"]).Pressure
                    logger.info(f"successfully converted depth data into pressure data")
                # see if parameter is a datalogger one and get from resampled flight directly
                # get aliases incase key doesn't match
                else:
                    try:
                        aliases = navigation_alias[key]
                    except KeyError:
                        logger.warning(f"no navigation aliases found for {key}")
                        aliases = []
                    aliases_casef = [alias.casefold() for alias in aliases]
                    for key2 in resampled_flight.keys():
                        if key2 in key.casefold() or key2 in aliases_casef:
                            track = resampled_flight[key2]
                    if track is None:
                        logger.warning(f"no interpolator found for parameter {key} marking parameter for removal from payload")
                        marked_keys.append(key)
                        continue
            # dont add errors to time
            if key != "TIME" and self.attrs.apply_obs_error:
                # add obs error
                logger.info(f"applying observation error to parameter {key}")
                # TODO need to handle sensor parameter specific values
                # find which sensor has this parameter stored.
                sensor_key = None
                for k3, sensor in self.platform.attrs.sensors.items():
                    if key in sensor.specification.keys():
                        sensor_key = k3
                        break
                track = simulate_sensor_error(model_t=track, mission_ts=self.attrs.mission_time_step,
                                              accuracy_bias=self.platform.attrs.sensors[sensor_key].specification[key]["accuracy"],
                                              resolution=self.platform.attrs.sensors[sensor_key].specification[key]["resolution"],
                                              drift_per_month=self.platform.attrs.sensors[sensor_key].specification[key]["drift_per_month"],
                                              m_min=self.platform.attrs.sensors[sensor_key].specification[key]["range"][0],
                                              m_max=self.platform.attrs.sensors[sensor_key].specification[key]["range"][1],
                                              percent_errors=self.platform.attrs.sensors[sensor_key].specification[key]["percent_errors"],
                                              noise_std=self.platform.attrs.sensors[sensor_key].specification[key]["noise_std"],)
                logger.info("observation error application successful")
            self.payload[key][:] = track

        for marked_key in marked_keys:
            logger.info(f"removing marked {marked_key} from payload")
            del self.payload[marked_key]

        #check for any alternative parameters and convert as needed
        conversion_to_apply = {}
        for world in self.worlds.attributes.matched_worlds.values():
            for alt_key, alt_parameter in world.alternative_parameter.items():
                if alt_parameter is not None:
                    logger.info(f"alternative parameter field in world attributes is not None, {alt_key} requires conversion from {alt_parameter}")
                    for k1, v1 in self.platform.attrs.sensors.items():
                        if alt_key in self.platform.attrs.sensors[k1].specification.keys():
                            conversion_to_apply[alt_key] = alt_parameter

        if conversion_to_apply:
            self.__convert_parameters(conversion_to_apply,flight=resampled_flight)

        logger.success(f"{self.attrs.mission} flown successfully")

    def export_payload(self,out_path:str):
        # Collect all 1D arrays into a DataFrame
        data = {name: self.payload[name][:] for name in self.payload.keys()}

        df = pd.DataFrame(data)

        # Save to CSV
        df.to_csv(out_path, index=False)

    def __convert_parameters(self, conversion_to_apply,flight):
        # TODO add other conversions here as needed.
        what_we_have = []
        what_we_need = []
        for k1,v1 in conversion_to_apply.items():
            what_we_have.append(v1)
            what_we_need.append(k1)
        if "CONSERVATIVE_TEMPERATURE" in what_we_have and "ABSOLUTE_SALINITY" in what_we_have:
            # need to convert from CT and AS
            if "INSITU_TEMPERATURE" in what_we_need and "PRACTICAL_SALINITY" in what_we_need:
                converted_tsp = ConvertedTSP.as_ct_2_it_ps(absolute_salinity=self.payload["PRACTICAL_SALINITY"][:],
                                                        conservative_temperature=self.payload["INSITU_TEMPERATURE"][:],
                                                        depth=flight["depth"],
                                                        latitude=flight["latitude"],
                                                        longitude=flight["longitude"], )
                self.payload["INSITU_TEMPERATURE"][:] = converted_tsp.Temperature
                self.payload["PRACTICAL_SALINITY"][:] = converted_tsp.Salinity

        elif "POTENTIAL_TEMPERATURE" in what_we_have:
            # need to convert from PT and PS
            if "INSITU_TEMPERATURE" in what_we_need:
                converted_tsp = ConvertedTSP.ps_pt_2_it_ps(practical_salinity=self.payload["PRACTICAL_SALINITY"][:],
                                                        potential_temperature=self.payload["INSITU_TEMPERATURE"][:],
                                                        depth=flight["depth"],
                                                        latitude=flight["latitude"],
                                                        longitude=flight["longitude"], )

                self.payload["PRACTICAL_SALINITY"][:] = converted_tsp.Salinity
                self.payload["INSITU_TEMPERATURE"][:] = converted_tsp.Temperature

        else:
            logger.warning(f"unknown conversion requested {conversion_to_apply}")
            logger.error(f"unable to convert alternative parameters {conversion_to_apply}")
            return
        logger.info(f"conversion of {what_we_have} to {what_we_need} successful")

    @staticmethod
    def _resample_flight(flight, new_interval_seconds):
        """
        Resample flight trajectory to a new time interval.

        Parameters:
            flight (dict): Dictionary containing 'longitude', 'latitude', 'depth', and 'time'.
            new_interval_seconds (int or float): The desired interval between samples in seconds.

        Returns:
            dict: A new flight dictionary with resampled data.
        """
        # Convert time to seconds since the first timestamp
        time_seconds = (flight["time"][:] - flight["time"][0])/np.timedelta64(1,'s')
        # Create new time array with specified interval
        new_time_seconds = np.arange(time_seconds[0], time_seconds[-1], new_interval_seconds)
        new_time = flight["time"][0] + new_time_seconds.astype('timedelta64[s]')

        # Interpolators
        lon_interp = interp1d(time_seconds, flight["longitude"], kind='linear', fill_value="extrapolate")
        lat_interp = interp1d(time_seconds, flight["latitude"], kind='linear', fill_value="extrapolate")
        depth_interp = interp1d(time_seconds, flight["depth"], kind='linear', fill_value="extrapolate")

        # Apply interpolation
        new_longitudes = lon_interp(new_time_seconds)
        new_latitudes = lat_interp(new_time_seconds)
        new_depths = depth_interp(new_time_seconds)

        # Return new flight data
        new_flight = {
            "longitude": new_longitudes,
            "latitude": new_latitudes,
            "depth": new_depths,
            "time": new_time
        }
        # Optional fields: Interpolate if they exist
        for key in ["pitch", "yaw", "roll"]:
            if key in flight:
                interp_func = interp1d(time_seconds, flight[key], kind='linear', fill_value="extrapolate")
                new_flight[key] = interp_func(new_time_seconds)

        return new_flight

    def show_payload(self, parameter: str = None, in_app: bool = False):
        """
        Creates an interactive plot of the AUV trajectory with the given parameters data mapped onto it using the
        specified colour map.

        Returns:
            Interactive plotly figure that opens in a web browser.
        """
        # Example parameters for the dropdown
        # Example parameters and their expected value ranges (cmin and cmax)
        parameters = {}
        if parameter is None:
            for key,payload in self.payload.items():

                parameters[key] = {"cmin": np.nanmin(payload[:]),
                                   "cmax": np.nanmax(payload[:])
                                   }

            # List of available color scales for the user to choose from
            colour_scales = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

            # Initial setup: first parameter and color scale
            initial_parameter = next(iter(self.payload.keys()))
            initial_colour_scale = "Jet"

            marker = {
                "size": 2,
                "color": np.array(self.payload[initial_parameter][:]),  # Ensuring its serializable
                "colorscale": initial_colour_scale,
                "cmin": parameters[initial_parameter]["cmin"],  # Set the minimum value for the color scale
                "cmax": parameters[initial_parameter]["cmax"],  # Set the maximum value for the color scale
                "opacity": 0.8,
                "colorbar": {"thickness": 40}
            }

            title = {
                "text": f"Payload: {initial_parameter}",
                "font": {"size": 30},
                "automargin": True,
                "yref": "paper"
            }

            scene = {
                "xaxis_title": "longitude",
                "yaxis_title": "latitude",
                "zaxis_title": "depth",
            }
            # TODO figure out how to dynamically set these rather than hardcoding platforms
            if self.platform.attrs.platform_type == "Slocum_G2" or self.platform.attrs.platform_type == "Slocum_G2_NonNMEA":
                latitude = "LATITUDE"
                longitude = "LONGITUDE"
                depth = "GLIDER_DEPTH"
            elif self.platform.attrs.platform_type == "ALR_1500":
                latitude = "ALATPT01"
                longitude = "ALONPT01"
                depth = "ADEPPT01"
            else:
                raise Exception(f"unsupported platform {self.platform.attrs.platform_type} for payload plotting")

            y =self.payload[latitude][:]
            x = self.payload[longitude][:]
            z = self.payload[depth][:]
            # Create the initial figure
            fig = go.Figure(data=[
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode='markers',
                    marker=marker
                )
            ])

            # Update the scene and layout
            fig.update_scenes(zaxis_autorange="reversed")
            fig.update_layout(title=title, scene=scene)
            # TODO fix the interaction between colour scales and parameters colour scale is not maintained when changing parameter
            # TODO it will always default to Jet colourscale
            # Define the dropdown for parameter selection
            parameter_dropdown = [
                {
                    "args": [
                        {"x": [self.payload[longitude][:]],  # Update x-coordinates
                         "y":[ self.payload[latitude][:]],  # Update y-coordinates
                         "z": [self.payload[depth][:]],
                         "marker.color": [np.array(self.payload[parameter][:])],
                         # Update the color for the new parameter
                         "marker.cmin": parameters[parameter]["cmin"],  # Set cmin for the new parameter
                         "marker.cmax": parameters[parameter]["cmax"],  # Set cmax for the new parameter
                         "marker.colorscale": initial_colour_scale},
                        # Keep the initial color scale (can be updated below)
                        {"title.text": f"Glider Payload: {parameter}"}  # Update the title to reflect the new parameter
                    ],
                    "label": parameter,
                    "method": "update"
                }
                for parameter in parameters
            ]

            # Define the dropdown for color scale selection
            color_scale_dropdown = [
                {
                    "args": [
                        {"marker.colorscale": colour_scale}  # Update the color scale for the current parameter
                    ],
                    "label": colour_scale,
                    "method": "restyle"
                }
                for colour_scale in colour_scales
            ]
            # Create text boxes for user to input cmin and cmax
            fig.update_layout(
                annotations=[
                    # Add labels for dropdowns
                    dict(text="Sensor:", x=0.05, y=1.2, showarrow=False, xref="paper", yref="paper",
                         font=dict(size=14)),
                    dict(text="Color Scale:", x=0.05, y=1.15, showarrow=False, xref="paper", yref="paper",
                         font=dict(size=14))
                ]
            )

            # Add both dropdowns to the layout
            fig.update_layout(
                updatemenus=[
                    {
                        "buttons": parameter_dropdown,
                        "direction": "down",
                        "showactive": True,
                        "x": 0.10,  # Adjust position for the parameter dropdown
                        "xanchor": "left",
                        "y": 1.20,
                        "yanchor": "top"
                    },
                    {
                        "buttons": color_scale_dropdown,
                        "direction": "down",
                        "showactive": True,
                        "x": 0.10,  # Adjust position for the color scale dropdown
                        "xanchor": "left",
                        "y": 1.15,
                        "yanchor": "top"
                    }
                ]
            )
        else:

            parameters[parameter] = {"cmin": np.nanmin(self.payload[parameter][:]),
                                     "cmax": np.nanmax(self.payload[parameter][:])
                                     }

            # List of available color scales for the user to choose from
            #colour_scales = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

            # Initial setup: first parameter and color scale
            initial_colour_scale = "Jet"

            marker = {
                "size": 2,
                "color": np.array(self.payload[parameter][:]),  # Ensuring its serializable
                "colorscale": initial_colour_scale,
                "cmin": parameters[parameter]["cmin"],  # Set the minimum value for the color scale
                "cmax": parameters[parameter]["cmax"],  # Set the maximum value for the color scale
                "opacity": 0.8,
                "colorbar": {"thickness": 40}
            }

            title = {
                "text": f"Payload: {parameter}",
                "font": {"size": 30},
                "automargin": True,
                "yref": "paper"
            }

            scene = {
                "xaxis_title": "longitude",
                "yaxis_title": "latitude",
                "zaxis_title": "depth",
            }
            # TODO figure out how to dynamically set these as they could be different parameters e.g. GLIDER_DEPTH
            if self.platform.attrs.platform_type == "Slocum_G2" or self.platform.attrs.platform_type == "Slocum_G2_NonNMEA":
                latitude = "LATITUDE"
                longitude = "LONGITUDE"
                depth = "GLIDER_DEPTH"
            elif self.platform.attrs.platform_type == "ALR_1500":
                latitude = "ALATPT01"
                longitude = "ALONPT01"
                depth = "ADEPPT01"
            else:
                raise Exception(f"unsupported platform {self.platform.attrs.platform_type} for payload plotting")

            y =self.payload[latitude][:]
            x = self.payload[longitude][:]
            z = self.payload[depth][:]
            # Create the initial figure
            fig = go.Figure(data=[
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode='markers',
                    marker=marker
                )
            ])
            # Update the scene and layout
            fig.update_scenes(zaxis_autorange="reversed")
            fig.update_layout(title=title, scene=scene)
        if not in_app:
            fig.show()
        else:
            return fig
        logger.info(f"successfully plotted payloads")

    def plot_trajectory(self, colour_scale: str = 'Viridis', ):
        """
        Created an interactive plot of the auv trajectory, with the datetime of the trajectory colour mapped onto it.

        Args:
            colour_scale: (optional) colour scale to use when plotting datetime onto trajectory

        Returns:
            interactive plotly figure that opens in a web browser.

        """
        marker = {
            "size": 2,
            "color": np.array(self.trajectory.time).tolist(),
            "colorscale": colour_scale,
            "opacity": 0.8,
            "colorbar": {"thickness": 40}
        }

        title = {
            "text": "Glider Trajectory",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper"
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }

        fig = go.Figure(
            data=[
                go.Scatter3d(x=self.trajectory.longitude, y=self.trajectory.latitude, z=self.trajectory.depth,
                             mode='markers', marker=marker)])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()

    def export_as_zarr(self, out_dir:str = None, store:zarr.storage.Store= None):
        """
        Exports mission to a zarr directory store
        Args:
            store:
            out_dir:

        Returns:
            void: zarr group is saved to directory store
        """
        if out_dir is None:
            out_dir = os.getcwd()

        # if store is provided assume it contains the campaign and add the mission group to it,
        # otherwise just create a store and create the mission group in it
        if store is None:
            store = zarr.storage.DirectoryStore(f"{out_dir}/{self.attrs.mission}.zarr")
            mission = zarr.group(store=store,overwrite=True)
        else:
            campaign = zarr.open_group(store=store)
            mission = campaign.create_group(f"{self.attrs.mission}",overwrite=True)


        # create subgroups
        payload = mission.create_group("payload")
        platform = mission.create_group("platform")
        trajectory = mission.create_group("trajectory")
        world = mission.create_group("world")

        # write mission attributes
        mission.attrs.update({"mission_attributes":unstructure(self.attrs)})
        mission.attrs.update({"geospatial_attributes":unstructure(self.geospatial_attrs)})
        mission.attrs.update({"navigation_keys":unstructure(self.navigation_keys)})

        # write platform attributes
        platform.attrs.update(unstructure(self.platform.attrs))

        # write platform data
        platform.array(name='behaviour',data=self.platform.behaviour)

        # write trajectory arrays
        trajectory.array(name="latitude",data=self.trajectory.latitude)
        trajectory.array(name="longitude",data=self.trajectory.longitude)
        trajectory.array(name="depth",data=self.trajectory.depth)
        trajectory.array(name="time",data=self.trajectory.time.astype('datetime64[s]'))
        trajectory.array(name="pitch",data=self.trajectory.pitch)
        trajectory.array(name="roll",data=self.trajectory.roll)
        trajectory.array(name="yaw",data=self.trajectory.yaw)

        # write payload arrays
        for pload in self.payload.keys():
            payload.array(name=pload,data=self.payload[pload])

        # update world attributes
        world.attrs.update(unstructure(self.worlds.attributes))
        # write world data
        for key, value in self.worlds.worlds.items():
            world.create_group(name=key)
            try:
                zarr.convenience.copy_all(value,world[key])
            except AttributeError:
                logger.warning(f"failed to copy world {key} trying to covert to zarr")
                del world[key]
                value.to_zarr(group=f"{world.name}/{key}",store=store)
                logger.info(f"successfully converted world {key} to zarr")


        # self.create_dim_map(msm_cat=msm_cat)
        # self.add_array_dimensions(group=self, dim_map=self.world.attrs['dim_map'])
        zarr.consolidate_metadata(store)
        logger.success(f"successfully exported {self.attrs.mission}")

