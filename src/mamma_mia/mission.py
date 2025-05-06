import os
from datetime import datetime
import numpy as np
import plotly.graph_objects as go
import xarray as xr
from attrs import define, frozen
from cattr import unstructure
from zarr import open_group

from mamma_mia import create_platform_class
from mamma_mia import create_sensor_class
import uuid
from loguru import logger
import zarr
from mamma_mia.catalog import Cats
from mamma_mia.interpolator import Interpolators
from mamma_mia.find_worlds import Worlds as Worlds2, SourceType
from mamma_mia.get_worlds import get_worlds
from mamma_mia.exceptions import CriticalParameterMissing,NoValidSource
from scipy.interpolate import interp1d

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
            # as the below is optional, they should not be None as this causes issues with exporting
            "pitch": "",
            "roll": "",
            "yaw": "",
        }

        for parameter_key, parameter in datalogger.parameters.items():
            combined_string = f"{parameter.parameter_id} {parameter.standard_name}".lower()
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
    def find_parameter_keys(parameter: str, platform_attrs, instrument_type: str = "data loggers") -> list[str]:
        sensor_key = None
        for key in platform_attrs.sensors.keys():
            if platform_attrs.sensors[key].instrument_type == instrument_type:
                sensor_key = key
                break

        parameter_keys = platform_attrs.sensors[sensor_key].parameters[parameter].source_names

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
    behaviour: np.ndarray

    @classmethod
    def from_xarray(cls, ds: xr.Dataset, navigation_keys: NavigationKeys):
        """
        Creates a trajectory from an xarray dataset
        Args:
            ds:
            navigation_keys:

        Returns:

        """
        latitude = cls.__add_source(ds=ds, source_keys=navigation_keys.latitude)
        longitude =cls.__add_source(ds=ds, source_keys=navigation_keys.longitude)
        depth = cls.__add_source(ds=ds, source_keys=navigation_keys.depth)
        # as time doesn't tend to have NaNs' filter based on latitude NaN's
        #time = ds[navigation_keys.time][~np.isnan(ds[navigation_keys.latitude])]
        time = cls.__add_source(ds=ds, source_keys=navigation_keys.time)

        if latitude.size != depth.size or longitude.size != depth.size or latitude.size != longitude.size:
            raise Exception("NaN filtering resulted in different sized navigation parameters")

        try:
            if navigation_keys.pitch is not None:
                pitch = cls.__add_source(ds=ds, source_keys=navigation_keys.pitch)
            else:
                logger.warning(f"Optional parameter pitch not specified in datalogger")
                pitch = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional pitch parameter for trajectory not found in simulated data: No variable named '{navigation_keys.pitch}'")
            pitch = np.zeros_like(depth)

        try:
            if navigation_keys.yaw is not None:
                yaw = cls.__add_source(ds=ds, source_keys=navigation_keys.yaw)
            else:
                logger.warning(f"Optional parameter yaw not specified in datalogger")
                yaw = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional yaw parameter for trajectory not found in simulated data: No variable named '{navigation_keys.yaw}'")
            yaw = np.zeros_like(depth)

        try:
            if navigation_keys.roll is not None:
                roll = cls.__add_source(ds=ds, source_keys=navigation_keys.roll)
            else:
                logger.warning(f"Optional parameter roll not specified in datalogger")
                roll = np.zeros_like(depth)
        except NoValidSource:
            logger.warning(
                f"Optional roll parameter for trajectory not found in simulated data: No variable named '{navigation_keys.roll}'")
            roll = np.zeros_like(depth)

        seconds_into_flight = (time - time[0]) / np.timedelta64(1, 's')
        # calculate changes in depth to determine platform behaviour
        dz = np.gradient(depth, seconds_into_flight)
        # TODO set these dynamically based on the platform
        ascent_thresh = 0.05  # m/s, adjust based on your system
        descent_thresh = -0.05  # m/s
        near_surface_thresh = 1
        # Using dz and set thresholds, create an event graph for the platform
        event = np.full_like(depth, 'hovering', dtype="S8")
        # Diving: dz < descent_thresh
        event[dz > descent_thresh] = 'diving'
        # Climbing: dz > ascent_thresh
        event[dz < ascent_thresh] = 'climbing'
        # Surfaced / Near surface: depth < threshold and nearly zero vertical speed
        surfaced_mask = (depth[:] < near_surface_thresh) & (np.abs(dz) < ascent_thresh)
        event[surfaced_mask] = 'surfaced'

        return cls(latitude=np.array(latitude, dtype=np.float64),
                   longitude=np.array(longitude, dtype=np.float64),
                   depth=np.array(depth, dtype=np.float64),
                   pitch=np.array(pitch, dtype=np.float64),
                   roll=np.array(roll, dtype=np.float64),
                   yaw=np.array(yaw, dtype=np.float64),
                   behaviour=np.array(event, dtype="S8"),
                   time=np.array(time, dtype=np.datetime64),
                   )

    @staticmethod
    def __add_source(ds: xr.Dataset, source_keys: list[str]):
        source = None
        for key in source_keys:
            try:
                source = ds[key][~np.isnan(ds[key])]
                break
            except KeyError:
                pass
        if source is None:
            raise NoValidSource("no valid source name found")
        return source

@frozen
class WorldExtent:
    lat_max: np.float64
    lat_min: np.float64
    lon_max: np.float64
    lon_min: np.float64
    time_start: str
    time_end: str
    depth_max: np.float64

@define
class WorldsAttributes:
    extent: WorldExtent
    catalog_priorities: dict
    interpolator_priorities: dict
    matched_worlds: dict

@define
class Worlds:
    attributes: WorldsAttributes
    worlds: dict
    stores: dict


@define
class Mission:
    platform: create_platform_class()
    attrs: MissionAttributes
    geospatial_attrs: GeospatialAttributes
    navigation_keys: NavigationKeys
    payload: dict[str, np.ndarray]
    worlds: Worlds
    trajectory: Trajectory

    @classmethod
    def from_campaign(cls,
                      mission: str,
                      summary: str,
                      title: str,
                      platform: create_platform_class(),
                      trajectory_path: str,
                      excess_space: int = 0.5,
                      extra_depth: int = 100,
                      msm_priority: int = 2,
                      cmems_priority: int = 1,
                      crs: str = 'EPSG:4326',
                      vertical_crs: str = 'EPSG:5831',
                      creator: Creator = Creator(),
                      publisher: Publisher = Publisher(),
                      contributor: Contributor = Contributor(),
                      standard_name_vocabulary = "https://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html"
                      ):
        instruments = []
        for instrument in platform.sensors.values():
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
                                      standard_name_vocabulary=standard_name_vocabulary
                                      )

        # find datalogger
        data_logger_key = None
        for sensor_key, sensor in platform.sensors.items():
            if sensor.instrument_type == "data loggers":
                data_logger_key = sensor_key
        if data_logger_key is None:
            raise Exception("No data logger found for this platform")

        # generate variable keys for navigation/trajectory variables in input dataset
        nav_keys = NavigationKeys.from_datalogger(datalogger=platform.sensors[data_logger_key],platform_attrs=platform)

        # generate trajectory
        ds = xr.open_dataset(attrs.trajectory_path)
        trajectory = Trajectory.from_xarray(ds=ds, navigation_keys=nav_keys)

        if platform.platform_type == "slocum":
            logger.info(f"Platform requires NEMA coordinate conversion")
            for i in range(trajectory.longitude.__len__()):
                trajectory.longitude[i] = cls.__convert_to_decimal(trajectory.longitude[i])
            for i in range(trajectory.latitude.__len__()):
                trajectory.latitude[i] = cls.__convert_to_decimal(trajectory.latitude[i])
            logger.success(f"Successfully converted from NEMA coordinates to decimal degrees")

        geospatial_attrs = GeospatialAttributes(
            geospatial_bounds_crs=crs,
            geospatial_bounds_vertical_crs=vertical_crs,
            geospatial_lat_max=np.max(trajectory.latitude),
            geospatial_lat_min=np.min(trajectory.latitude),
            geospatial_lat_units=cls.get_parameter_units(platform_attrs=platform ,parameter="latitude"),
            geospatial_lon_max=np.max(trajectory.longitude),
            geospatial_lon_min=np.min(trajectory.longitude),
            geospatial_lon_units=cls.get_parameter_units(platform_attrs=platform,parameter="longitude"),
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
        worlds = Worlds(
            attributes=WorldsAttributes(extent=extent,
                                                 catalog_priorities={"msm": msm_priority, "cmems": cmems_priority},
                                                 matched_worlds={},
                                                 interpolator_priorities={}
                                                 ),
            worlds={},
            stores={}
        )
        payload = {}
        # total mission time in seconds (largest that a payload array could be)
        mission_total_time_seconds = (trajectory.time[-1] - trajectory.time[0]).astype('timedelta64[s]')
        for name, sensor in platform.sensors.items():
            for name2, parameter in sensor.parameters.items():
                # Don't create a payload array for any time parameters since seconds for each sensor sample are stored in each payload array
                # TODO fix this so that time parameter aliases are checked not just hardcoded
                if name2 in ["time","ATIMPT01"]:
                    continue
                payload[name2] = np.empty(shape=(2, mission_total_time_seconds.astype(int) + 1), dtype=np.float64)
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
    def get_parameter_units(platform_attrs,parameter: str, instrument_type: str = "data loggers") -> str:
        sensor_key = None
        parameter_units = None
        for key in platform_attrs.sensors.keys():
            if platform_attrs.sensors[key].instrument_type == instrument_type:
                sensor_key = key
                break
        try:
            parameter_units = platform_attrs.sensors[sensor_key].parameters[parameter].unit_of_measure
        except KeyError:
            for val in platform_attrs.sensors[sensor_key].parameters.values():
                try:
                    if parameter in val.parameter_definition.lower():
                        parameter_units = val.unit_of_measure
                except AttributeError:
                    if parameter in val.long_name.lower():
                        parameter_units = val.units

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
        matched_worlds = Worlds2()
        source = SourceType.from_string("cmems")
        local_dir = "rapid_data"
        matched_worlds.search_worlds(cat=cat, payload=self.payload, extent=self.worlds.attributes.extent,source=source,local_dir=local_dir)
        self.worlds.attributes.matched_worlds = matched_worlds.entries
        data_stores = get_worlds(cat=cat, worlds=self.worlds)
        self.worlds.stores = data_stores

    def fly(self, interpolator: Interpolators):
        """

        Args:

            interpolator: Interpolator object with interpolators to fly through

        Returns:
            void: mission object with filled reality arrays of interpolated data, i.e. AUV has flown its
                  mission through the world.
        """
        logger.info(f"flying {self.attrs.mission} using {self.platform.entity_name}")
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

        sample_rate = 1
        navigation_keys = []
        navigation_alias = {}
        # get navigation keys and any aliases that relate to them
        for k1, v1 in self.platform.sensors.items():
            if self.platform.sensors[k1].instrument_type == "data loggers":
                navigation_keys = list(self.platform.sensors[k1].parameters.keys())
                for k2, parameter in self.platform.sensors[k1].parameters.items():
                    for nav_key in navigation_keys:
                        if nav_key == parameter.parameter_id:
                            navigation_alias[nav_key] = parameter.alternate_labels
        marked_keys = []
        for key in self.payload.keys():
            for k1, v1 in self.platform.sensors.items():
                if key in self.platform.sensors[k1].parameters.keys():
                    sample_rate = self.platform.sensors[k1].sample_rate
                    # if a sample rate has not been explicitly set use the max rate of the sensor
                    if sample_rate == -999:
                        sample_rate = self.platform.sensors[k1].max_sample_rate

            resampled_flight = self._resample_flight(flight=flight, new_interval_seconds=sample_rate)
            # subset flight to only what is needed for interpolation (position rather than orientation)
            flight_subset = {key: resampled_flight[key] for key in ["longitude", "latitude", "depth", "time"]}
            try:
                logger.info(f"flying through {key} world and creating interpolated data for flight")
                track = interpolator.interpolator[key].quadrivariate(flight_subset)
            except KeyError:
                track = None
                # see if parameter is a datalogger one and get from resampled flight directly
                # get aliases incase key doesn't match
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

            # Convert time to seconds from the start
            seconds_into_mission = (resampled_flight["time"] - resampled_flight["time"][0]) / np.timedelta64(1, 's')

            # Ensure they have the same length
            try:
                assert len(track) == len(seconds_into_mission), "Arrays must have the same length"
            except AssertionError:
                logger.error("track and time arrays must have same length")
                raise Exception

            n = len(track)

            apply_events = True
            if key in navigation_keys:
                apply_events = False

            if apply_events:
                # adjust sampling based on platform behaviour, e.g. only retain upcast or downcasts etc.
                events = self.trajectory.behaviour[:].astype(str)
                event_idx_for_payload = np.searchsorted(flight["time"], resampled_flight["time"], side="right") - 1
                event_idx_for_payload = np.clip(event_idx_for_payload, 0, flight["time"].__len__() - 1)
                event_at_payload = events[event_idx_for_payload]
                event_mask = np.isin(event_at_payload, self.platform.sensor_behaviour.value)
                n = len(track[event_mask])
                self.payload[key][0, :n] = seconds_into_mission[event_mask]
                self.payload[key][1, :n] = track[event_mask]
                self.payload[key] = self.payload[key][:, :n]

            else:
                self.payload[key][0, :n] = seconds_into_mission
                self.payload[key][1, :n] = track
                self.payload[key] = self.payload[key][:, :n]

        for marked_key in marked_keys:
            logger.info(f"removing marked {marked_key} from payload")
            del self.payload[marked_key]

        logger.success(f"{self.attrs.mission} flown successfully")

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
        time_seconds = (flight["time"] - flight["time"][0]) / np.timedelta64(1, 's')

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

                parameters[key] = {"cmin": np.nanmin(payload[1, :]),
                                   "cmax": np.nanmax(payload[1, :])
                                   }

            # List of available color scales for the user to choose from
            colour_scales = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

            # Initial setup: first parameter and color scale
            initial_parameter = next(iter(self.payload.keys()))
            initial_colour_scale = "Jet"

            marker = {
                "size": 2,
                "color": np.array(self.payload[initial_parameter][1, :]),  # Ensuring its serializable
                "colorscale": initial_colour_scale,
                "cmin": parameters[initial_parameter]["cmin"],  # Set the minimum value for the color scale
                "cmax": parameters[initial_parameter]["cmax"],  # Set the maximum value for the color scale
                "opacity": 0.8,
                "colorbar": {"thickness": 40}
            }

            title = {
                "text": f"Glider Payload: {initial_parameter}",
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
            # TODO basically the payload needs to be able to handle parameters aliases
            x = np.interp(self.payload[initial_parameter][0, :], self.payload["LON"][0, :],
                          self.payload["LON"][1, :])
            y = np.interp(self.payload[initial_parameter][0, :], self.payload["LAT"][0, :],
                          self.payload["LAT"][1, :])
            z = np.interp(self.payload[initial_parameter][0, :], self.payload["DEPTH"][0, :],
                          self.payload["DEPTH"][1, :])
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
                        {"x": [np.interp(self.payload[parameter][0, :], self.payload["LON"][0, :],
                                         self.payload["LON"][1, :])],  # Update x-coordinates
                         "y": [np.interp(self.payload[parameter][0, :], self.payload["LAT"][0, :],
                                         self.payload["LAT"][1, :])],  # Update y-coordinates
                         "z": [np.interp(self.payload[parameter][0, :], self.payload["DEPTH"][0, :],
                                         self.payload["DEPTH"][1, :])],
                         "marker.color": [np.array(self.payload[parameter][1, :])],
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

            parameters[parameter] = {"cmin": np.nanmin(self.payload[parameter][1, :]),
                                     "cmax": np.nanmax(self.payload[parameter][1, :])
                                     }

            # List of available color scales for the user to choose from
            colour_scales = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

            # Initial setup: first parameter and color scale
            initial_colour_scale = "Jet"

            marker = {
                "size": 2,
                "color": np.array(self.payload[parameter][1, :]),  # Ensuring its serializable
                "colorscale": initial_colour_scale,
                "cmin": parameters[parameter]["cmin"],  # Set the minimum value for the color scale
                "cmax": parameters[parameter]["cmax"],  # Set the maximum value for the color scale
                "opacity": 0.8,
                "colorbar": {"thickness": 40}
            }

            title = {
                "text": f"ALR Payload: {parameter}",
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
            # TODO basically the payload needs to be able to handle parameters aliases
            x = np.interp(self.payload[parameter][0, :], self.payload["ALONPT01"][0, :],
                          self.payload["ALONPT01"][1, :])
            y = np.interp(self.payload[parameter][0, :], self.payload["ALATPT01"][0, :],
                          self.payload["ALATPT01"][1, :])
            z = np.interp(self.payload[parameter][0, :], self.payload["ADEPPT01"][0, :],
                          self.payload["ADEPPT01"][1, :])
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
        logger.success(f"successfully plotted payloads")

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
            campaign = open_group(store=store)
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
        platform.attrs.update(unstructure(self.platform))

        # write trajectory arrays
        trajectory.array(name="latitude",data=self.trajectory.latitude)
        trajectory.array(name="longitude",data=self.trajectory.longitude)
        trajectory.array(name="depth",data=self.trajectory.depth)
        trajectory.array(name="time",data=self.trajectory.time)
        trajectory.array(name="pitch",data=self.trajectory.pitch)
        trajectory.array(name="roll",data=self.trajectory.roll)
        trajectory.array(name="yaw",data=self.trajectory.yaw)
        trajectory.array(name='behaviour',data=self.trajectory.behaviour)

        # write payload arrays
        for pload in self.payload.keys():
            payload.array(name=pload,data=self.payload[pload])

        # update world attributes
        world.attrs.update(unstructure(self.worlds.attributes))
        # write world data
        for key, value in self.worlds.worlds.items():
            world.create_group(name=key)
            zarr.convenience.copy_all(value,world[key])

        # self.create_dim_map(msm_cat=msm_cat)
        # self.add_array_dimensions(group=self, dim_map=self.world.attrs['dim_map'])
        zarr.consolidate_metadata(store)
        logger.success(f"successfully exported {self.attrs.mission}")

    def export_to_nc(self, outname=None):
        pass
        # if outname is None:
        #     name = self.attrs['mission']
        # else:
        #     name = outname
        # logger.info(f"exporting mission {self.attrs['mission']} to {name}.nc")
        # ds = xr.open_zarr(store=self.store)
        # ds.to_netcdf(f"{name}.nc")
        # logger.success(f"successfully exported {self.attrs['mission']} as netcdf file")

    # # From: https://github.com/smerckel/latlon/blob/main/latlon/latlon.py
    # # Lucas Merckelbach
    # @staticmethod
    # def __convert_to_decimal(x):
    #     """
    #     Converts a latitude or longitude in NMEA format to decimal degrees
    #     """
    #     sign = np.sign(x)
    #     x_abs = np.abs(x)
    #     degrees = np.floor(x_abs / 100.)
    #     minutes = x_abs - degrees * 100
    #     decimal_format = degrees + minutes / 60.
    #     return decimal_format * sign

    def create_dim_map(self, msm_cat):
        """
        Creates a dimension mapping dictionary and updates the relevant attribute in the world group. This attribute is
        required to enable Xarray to read the zarr groups of the campaign object.
        Args:
            msm_cat: msm intake catalog

        Returns:
            void: updates the dim_map attribute of the world zarr group
        """
        pass
        # example dim map that needs to generated
        # dim_map = {
        #     f"{mission.attrs['name']}/reality/nitrate": ['time'],
        #     f"{mission.attrs['name']}/reality/phosphate": ['time'],
        #     f"{mission.attrs['name']}/reality/pressure": ['time'],
        #     f"{mission.attrs['name']}/reality/salinity": ['time'],
        #     f"{mission.attrs['name']}/reality/silicate": ['time'],
        #     f"{mission.attrs['name']}/reality/temperature": ['time'],
        #     f"{mission.attrs['name']}/trajectory/datetimes": ['time'],
        #     f"{mission.attrs['name']}/trajectory/depths": ['time'],
        #     f"{mission.attrs['name']}/trajectory/latitudes": ['time'],
        #     f"{mission.attrs['name']}/trajectory/longitudes": ['time'],
        #     f"{mission.attrs['name']}/world/cmems_mod_glo_bgc_my_0.25deg_P1D-m/no3": ['time', 'depth','latitude','longitude'],
        #     f"{mission.attrs['name']}/world/cmems_mod_glo_bgc_my_0.25deg_P1D-m/po4": ['time', 'depth', 'latitude', 'longitude'],
        #     f"{mission.attrs['name']}/world/cmems_mod_glo_bgc_my_0.25deg_P1D-m/si": ['time', 'depth', 'latitude', 'longitude'],
        #     f"{mission.attrs['name']}/world/cmems_mod_glo_phy_my_0.083deg_P1D-m/so": ['time', 'depth', 'latitude', 'longitude'],
        #     f"{mission.attrs['name']}/world/cmems_mod_glo_phy_my_0.083deg_P1D-m/thetao": ['time', 'depth', 'latitude', 'longitude'],
        #     f"{mission.attrs['name']}/world/msm_eORCA12/so": ['time_counter','deptht','latitude','longitude'],
        #     f"{mission.attrs['name']}/world/msm_eORCA12/thetao": ['time_counter', 'deptht', 'latitude', 'longitude'],
        # }
        # TODO need to figure out how to dynamically set the dimensions in the mapping attribute as these could change
        # TODO Also ideally need to do the other variables in the world datasets e.g. time, depth etc
        # dim_map = {}
        # for k2, v2 in self.payload.items():
        #     dim_map[f"{self.attrs['mission']}/payload/{k2}"] = ['time']
        # for k3, v3 in self.trajectory.items():
        #     dim_map[f"{self.attrs['mission']}/trajectory/{k3}"] = ['time']
        # for k4, v4 in self.world.items():
        #     split_key = k4.split('_')
        #     for k5, v5 in v4.items():
        #         if split_key[0] == "cmems":
        #             # TODO a much better job than this hacky mess...
        #             aliases = []
        #             for val in inventory.parameters.entries.values():
        #                 for alias in val.alias:
        #                     aliases.append(alias)
        #             if [k5] in aliases:
        #                 dim_map[f"{self.attrs['mission']}/world/{k4}/{k5}"] = ['time', 'depth', 'latitude', 'longitude']
        #         elif split_key[0] == "msm":
        #             msm_metadata = msm_cat[k4].describe()['metadata']
        #             msm_alias = msm_metadata.get('aliases', [])
        #             if k5 in msm_alias.keys():
        #                 dim_map[f"{self.attrs['mission']}/world/{k4}/{k5}"] = ['time_counter', 'deptht', 'latitude',
        #                                                                        'longitude']
        #         else:
        #             logger.error(f"unknown model source key {k5}")
        #             raise UnknownSourceKey
        # self.world.attrs.update({"dim_map": dim_map})

    def add_array_dimensions(self, group, dim_map, path=""):
        """
        Recursively add _ARRAY_DIMENSIONS attribute to all arrays in a Zarr group, including nested groups.

        Args:
            group (zarr.Group): The root Zarr group to start with.
            dim_map (dict): A dictionary mapping array paths to their corresponding dimension names.
            path (str): The current path in the group hierarchy (used to track nested groups).

        Returns:
            void: updates the _ARRAY_DIMENSIONS attribute of the world zarr group required by xarray
        """
        for name, item in group.items():
            # Construct the full path by appending the current item name
            full_path = f"{path}/{name}" if path else name

            # If the item is a group, recurse into it
            if isinstance(item, zarr.Group):
                self.add_array_dimensions(item, dim_map, full_path)
            # If the item is an array, add the _ARRAY_DIMENSIONS attribute
            elif isinstance(item, zarr.Array):
                if full_path in dim_map:
                    item.attrs["_ARRAY_DIMENSIONS"] = dim_map[full_path]
                    logger.info(f"Added _ARRAY_DIMENSIONS to {full_path}: {dim_map[full_path]}")
                else:
                    logger.warning(f"No dimension information found for {full_path}")
