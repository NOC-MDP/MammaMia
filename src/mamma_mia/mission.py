import numpy as np
import plotly.graph_objects as go
import xarray as xr
from cattrs import unstructure
from attrs import define
from mamma_mia import create_platform_class
import uuid
from loguru import logger
import zarr
from mamma_mia.catalog import Cats
from mamma_mia.interpolator import Interpolators
from mamma_mia.find_worlds import find_worlds
from mamma_mia.get_worlds import get_worlds
from mamma_mia.exceptions import UnknownSourceKey, CriticalParameterMissing, DataloggerNotFound
from scipy.interpolate import interp1d
from datetime import datetime


@define
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


@define
class Contributor:
    """
    stores details of mission contributor
    """
    email: str = "mm2@mm.ac.uk"
    name: str = "mm2"
    role: str = "Principal Investigator"
    role_vocab: str = ""


@define
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


class Mission(zarr.Group):
    """
    Mission object, this contains all the components to be able to fly an AUV mission (generate interpolated data)

    Args:
        mission: name of the mission
        summary: description of the mission
        trajectory_path: path of the AUV trajectory netcdf file
    Optional:
        store: set zarr store here, by default it will store in memory
        overwrite: overwrite existing zarr store if present
        excess_space: amount of area to exceed trajectory by when downloading subset in decimal degrees
        excess_depth: amount of depth to exceed trajectory by when downloading subset in metres
        msm_priority: priority value of msm source data (higher has more priority)
        cmems_priority: priority value of cmems source data (higher has more priority)

    Returns:
        Mission object: consisting of a zarr group containing initialised attributes and arrays of trajectory data
        and initialised arrays ready for reality data

    """

    def __init__(self,
                 mission: str,
                 summary: str,
                 title: str,
                 platform: create_platform_class(),
                 trajectory_path: str,
                 store=None,
                 overwrite=False,
                 excess_space: int = 0.5,
                 extra_depth: int = 100,
                 msm_priority: int = 2,
                 cmems_priority: int = 1,
                 crs: str = 'EPSG:4326',
                 vertical_crs: str = 'EPSG:5831',
                 creator: Creator = Creator(),
                 publisher: Publisher = Publisher(),
                 contributor: Contributor = Contributor(),
                 ):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        # general mission metadata
        self.attrs["mission"] = mission
        self.attrs["internal_mission_identifier"] = str(uuid.uuid4())
        self.attrs["summary"] = summary
        self.attrs["title"] = title
        self.attrs["date_created"] = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S.%f")

        self.attrs["contributor_email"] = contributor.email
        self.attrs["contributor_name"] = contributor.name
        self.attrs["contributor_role"] = contributor.role
        self.attrs["contributor_role_vocabulary"] = contributor.role_vocab

        self.attrs["creator_email"] = creator.email
        self.attrs["creator_institution"] = creator.institution
        self.attrs["creator_name"] = creator.name
        self.attrs["creator_type"] = creator.creator_type
        self.attrs["creator_url"] = creator.url

        self.attrs["publisher_email"] = publisher.email
        self.attrs["publisher_name"] = publisher.name
        self.attrs["publisher_type"] = publisher.type
        self.attrs["publisher_url"] = publisher.url

        self.attrs["standard_name_vocabulary"] = "https://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html"

        # create platform attributes from platform class
        platform2 = self.create_group("platform")
        platform_unstruct = unstructure(platform)
        platform2.attrs.update(platform_unstruct)
        self.attrs["platform"] = platform2.attrs["platform_family"]
        self.attrs["wmoid"] = platform2.attrs["wmo_platform_code"]

        # find datalogger
        data_logger_key = None
        for sensor_key, sensor in platform_unstruct["sensors"].items():
            if sensor["instrument_type"] == "data loggers":
                data_logger_key = sensor_key
        # look up dict for navigation parameters linking, parameter to source trajectory and MM trajectory group
        navigation = {
            "latitude": "",
            "longitude": "",
            "depth": "",
            "time": "",
            "pitch": "",
            "roll": "",
            "yaw": ""
        }
        # for each datalogger parameter get the source key for dataset and try to match to navigation by checking definition and long name
        if data_logger_key is not None:
            for parameter_key, parameter in platform_unstruct["sensors"][data_logger_key]["parameters"].items():
                ds_key = self.find_parameter_key(parameter=parameter_key)
                for nav in navigation:
                    try:
                        if nav in parameter["parameter_definition"].lower():
                            navigation[nav] = ds_key
                    except KeyError:
                        try:
                            if nav in parameter["long_name"].lower():
                                navigation[nav] = ds_key
                        except KeyError:
                            raise Exception("unable to determine navigation definition")
        else:
            logger.error("was unable to find an instrument of type data loggers in platform payload")
            raise DataloggerNotFound

        # create trajectory group from input simulated trajectory and sensor/parameter metadata
        ds = xr.open_dataset(trajectory_path)
        trajectory = self.create_group("trajectory")
        try:
            trajectory.array(name="latitude", data=np.array(ds[navigation["latitude"]]))
            trajectory.array(name="longitude", data=np.array(ds[navigation["longitude"]]))
            trajectory.array(name="depth", data=np.array(ds[navigation["depth"]]))
            trajectory.array(name="time", data=np.array(ds[navigation["time"]], dtype='datetime64'))
        except KeyError as e:
            logger.error(f"Critical parameter for trajectory missing: {e}")
            raise CriticalParameterMissing

        try:
            if navigation["pitch"] != "":
                trajectory.array(name="pitch", data=np.array(ds[navigation["pitch"]]))
            else:
                logger.warning(f"Optional parameter pitch not specified in datalogger")
        except KeyError:
            logger.warning(
                f"Optional pitch parameter for trajectory not found in simulated data: No variable named '{navigation['pitch']}'")

        try:
            if navigation["yaw"] != "":
                trajectory.array(name="yaw", data=np.array(ds[navigation["yaw"]]))
            else:
                logger.warning(f"Optional parameter yaw not specified in datalogger")
        except KeyError:
            logger.warning(
                f"Optional yaw parameter for trajectory not found in simulated data: No variable named '{navigation['yaw']}'")

        try:
            if navigation["roll"] != "":
                trajectory.array(name="roll", data=np.array(ds[navigation["roll"]]))
            else:
                logger.warning(f"Optional parameter roll not specified in datalogger")
        except KeyError:
            logger.warning(
                f"Optional roll parameter for trajectory not found in simulated data: No variable named '{navigation['roll']}'")

        # TODO this most likely will only be needed for specific simulator inputs.
        # convert from glider format to decimal degrees
        for i in range(trajectory.longitude.__len__()):
            trajectory.longitude[i] = self.__convert_to_decimal(trajectory.longitude[i])
        for i in range(trajectory.latitude.__len__()):
            trajectory.latitude[i] = self.__convert_to_decimal(trajectory.latitude[i])

        # write geospatial meta data
        self.attrs["geospatial_bounds_crs"] = crs
        self.attrs["geospatial_bounds_vertical_crs"] = vertical_crs
        self.attrs["geospatial_lat_max"] = np.max(trajectory.latitude)
        self.attrs["geospatial_lat_min"] = np.min(trajectory.latitude)
        self.attrs["geospatial_lat_units"] = self.get_parameter_units(parameter="latitude")
        self.attrs["geospatial_lon_min"] = np.min(trajectory.longitude)
        self.attrs["geospatial_lon_max"] = np.max(trajectory.longitude)
        self.attrs["geospatial_lon_units"] = self.get_parameter_units(parameter="longitude")
        self.attrs["geospatial_vertical_max"] = np.max(trajectory.depth)
        self.attrs["geospatial_vertical_min"] = np.min(trajectory.depth)
        self.attrs["geospatial_vertical_units"] = "m"

        self.attrs["Westernmost_Easting"] = np.min(trajectory.longitude)
        self.attrs["Easternmost_Easting"] = np.max(trajectory.longitude)
        self.attrs["Northernmost_Northing"] = np.max(trajectory.latitude)
        self.attrs["Southernmost_Northing"] = np.min(trajectory.latitude)

        self.attrs["geospatial_bounds"] = (f"POLYGON(({self.attrs['geospatial_lon_min']},"
                                           f"{self.attrs['geospatial_lon_max']},"
                                           f"{self.attrs['geospatial_lat_min']},"
                                           f"{self.attrs['geospatial_lat_max']},))")

        self.attrs["time_coverage_start"] = np.datetime_as_string(trajectory.time[0], unit="s")
        self.attrs["time_coverage_end"] = np.datetime_as_string(trajectory.time[-1], unit="s")

        self.attrs["featureType"] = "Trajectory"

        instruments = []
        for instrument in platform2.attrs["sensors"].values():
            instruments.append(instrument["sensor_name"])

        self.attrs["instruments"] = instruments
        # create empty world group
        worlds = self.create_group("world")
        extent = {
            "max_lat": np.around(np.max(trajectory.latitude), 2) + excess_space,
            "min_lat": np.around(np.min(trajectory.latitude), 2) - excess_space,
            "max_lng": np.around(np.max(trajectory.longitude), 2) + excess_space,
            "min_lng": np.around(np.min(trajectory.longitude), 2) - excess_space,
            # TODO dynamically set the +/- delta on start and end time based on time step of model (need at least two time steps)
            "start_time": np.datetime_as_string(trajectory.time[0] - np.timedelta64(30, 'D'), unit="D"),
            "end_time": np.datetime_as_string(trajectory.time[-1] + np.timedelta64(30, 'D'), unit="D"),
            "max_depth": np.around(np.max(trajectory.depth), 2) + extra_depth,
        }
        worlds.attrs["extent"] = extent
        worlds.attrs["catalog_priorities"] = {"msm": msm_priority, "cmems": cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}
        worlds.attrs["dim_map"] = {}

        payload = self.create_group("payload")

        # total mission time in seconds (largest that a payload array could be)
        mission_total_time_seconds = (trajectory.time[-1] - trajectory.time[0]).astype('timedelta64[s]')

        for name, sensor in platform.sensors.items():
            for name2, parameter in sensor.parameters.items():
                # Don't create a payload array for any time parameters since seconds for each sensor sample are stored in each payload array
                if "TIME" in name2:
                    continue
                payload.empty(name=name2, shape=(2, mission_total_time_seconds.astype(int)), dtype=np.float64)

    def find_parameter_key(self, parameter: str, instrument_type: str = "data loggers") -> str:
        sensor_key = None
        parameter_key = None
        for key in self.platform.attrs["sensors"].keys():
            if self.platform.attrs["sensors"][key]["instrument_type"] == instrument_type:
                sensor_key = key
                break
        try:
            parameter_key = self.platform.attrs["sensors"][sensor_key]["parameters"][parameter]["source_name"]
        except KeyError:
            for key in self.platform.attrs["sensors"][sensor_key]["parameters"].keys():
                if key.startswith(parameter) or key.endswith(parameter):
                    try:
                        parameter_key = self.platform.attrs["sensors"][sensor_key]["parameters"][key]["source_name"]
                    except KeyError:
                        parameter_key = self.platform.attrs["sensors"][sensor_key]["parameters"][key]["standard_name"]
        return parameter_key

    def get_parameter_units(self, parameter: str, instrument_type: str = "data loggers") -> str:
        sensor_key = None
        parameter_units = None
        for key in self.platform.attrs["sensors"].keys():
            if self.platform.attrs["sensors"][key]["instrument_type"] == instrument_type:
                sensor_key = key
                break
        try:
            parameter_units = self.platform.attrs["sensors"][sensor_key]["parameters"][parameter]["unit_of_measure"]
        except KeyError:
            for val in self.platform.attrs["sensors"][sensor_key]["parameters"].values():
                try:
                    if parameter in val["parameter_definition"].lower():
                        parameter_units = val["unit_of_measure"]
                except KeyError:
                    if parameter in val["long_name"].lower():
                        parameter_units = val["units"]

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
        matched_worlds = find_worlds(cat=cat, reality=self.payload, extent=self.world.attrs["extent"])
        self.world.attrs.update({"matched_worlds": unstructure(matched_worlds)})
        zarr_stores = get_worlds(cat=cat, world=self.world)
        self.world.attrs.update({"zarr_stores": zarr_stores})

    def fly(self, interpolator: Interpolators):
        """

        Args:

            interpolator: Interpolator object with interpolators to fly through

        Returns:
            void: mission object with filled reality arrays of interpolated data, i.e. AUV has flown its
                  mission through the world.
        """
        logger.info(f"flying {self.attrs['mission']} using {self.platform.attrs['entity_name']}")
        # build orientation arrays, if missing from trajectory replace with zeros
        try:
            pitch = np.array(self.trajectory["pitch"])
        except KeyError:
            pitch = np.zeros(shape=self.trajectory["latitude"].__len__())
        try:
            yaw = np.array(self.trajectory["yaw"])
        except KeyError:
            yaw = np.zeros(shape=self.trajectory["latitude"].__len__())
        try:
            roll = np.array(self.trajectory["roll"])
        except KeyError:
            roll = np.zeros(shape=self.trajectory["latitude"].__len__())
        flight = {
            "longitude": np.array(self.trajectory["longitude"]),
            "latitude": np.array(self.trajectory["latitude"]),
            "depth": np.array(self.trajectory["depth"]),
            "pitch": pitch,
            "yaw": yaw,
            "roll": roll,
            "time": np.array(self.trajectory["time"], dtype='datetime64'),
        }
        sample_rate = 1
        for key in self.payload.array_keys():
            for k1, v1 in self.platform.attrs["sensors"].items():
                if key in self.platform.attrs["sensors"][k1]["parameters"].keys():
                    sample_rate = self.platform.attrs["sensors"][k1]["sample_rate"]
                    # if a sample rate has not been explicitly set use the max rate of the sensor
                    if sample_rate == -999:
                        sample_rate = self.platform.attrs["sensors"][k1]["max_sample_rate"]

            resampled_flight = self._resample_flight(flight=flight, new_interval_seconds=sample_rate)
            # subset flight to only what is needed for interpolation (position rather than orientation)
            flight_subset = {key: resampled_flight[key] for key in ["longitude", "latitude", "depth", "time"]}
            try:
                logger.info(f"flying through {key} world and creating interpolated data for flight")
                track = interpolator.interpolator[key].quadrivariate(flight_subset)
            except KeyError:
                track = None
                for key2 in resampled_flight.keys():
                    if key2 in key.lower() or key2 in key:
                        track = resampled_flight[key2]
                if track is None:
                    logger.warning(f"no interpolator found for parameter {key} removing from payload")
                    try:
                        del (self.payload[key])
                    # this exception seems to always occur when calling delete on zarr array?
                    except KeyError:
                        continue
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

            # Update the first n elements of the Zarr array
            self.payload[key][0, :n] = seconds_into_mission
            self.payload[key][1, :n] = track

            # Trim the Zarr array to the new length
            self.payload[key].resize((2, n))

        logger.success(f"{self.attrs['mission']} flown successfully")

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

    def show_payload(self):
        """
        Creates an interactive plot of the AUV trajectory with the given parameters data mapped onto it using the
        specified colour map.

        Returns:
            Interactive plotly figure that opens in a web browser.
        """
        # Example parameters for the dropdown
        # Example parameters and their expected value ranges (cmin and cmax)
        # TODO dynamically build this from payload group

        parameters = {
            "TEMP": {"cmin": np.round(np.nanmin(self.payload["TEMP"][1, :]), 2),
                     "cmax": np.round(np.nanmax(self.payload["TEMP"][1, :]), 2)},
            "CNDC": {"cmin": np.round(np.nanmin(self.payload["CNDC"][1, :]), 2),
                     "cmax": np.round(np.nanmax(self.payload["CNDC"][1, :]), 2)},
        }

        # List of available color scales for the user to choose from
        colour_scales = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

        # Initial setup: first parameter and color scale
        initial_parameter = "TEMP"
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
        x = np.interp(self.payload[initial_parameter][0, :], self.payload["LONGITUDE"][0, :],
                      self.payload["LONGITUDE"][1, :])
        y = np.interp(self.payload[initial_parameter][0, :], self.payload["LATITUDE"][0, :],
                      self.payload["LATITUDE"][1, :])
        z = np.interp(self.payload[initial_parameter][0, :], self.payload["GLIDER_DEPTH"][0, :],
                      self.payload["GLIDER_DEPTH"][1, :])
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
                    {"marker.color": [np.array(self.payload[parameter][1, :])],
                     # Update the color for the new parameter
                     "marker.cmin": parameters[parameter]["cmin"],  # Set cmin for the new parameter
                     "marker.cmax": parameters[parameter]["cmax"],  # Set cmax for the new parameter
                     "marker.colorscale": initial_colour_scale},  # Keep the initial color scale (can be updated below)
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
                dict(text="Sensor:", x=0.05, y=1.2, showarrow=False, xref="paper", yref="paper", font=dict(size=14)),
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
        fig.show()
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
                go.Scatter3d(x=self.trajectory["longitude"], y=self.trajectory["latitude"], z=self.trajectory["depth"],
                             mode='markers', marker=marker)])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()

    def export(self, cmems_alias, msm_cat, store: zarr.DirectoryStore = None):
        """
        Exports mission to a zarr directory store
        Args:
            store: path to save mission zarr group too.
            cmems_alias:
            msm_cat:

        Returns:
            void: zarr group is saved to directory store
        """
        if store is None:
            export_store = zarr.DirectoryStore(f"{self.attrs['mission']}.zarr")
        else:
            export_store = store
        logger.info(f"exporting mission {self.attrs['mission']} to {export_store}")
        zarr.copy_store(self.store, export_store)
        self.create_dim_map(cmems_alias=cmems_alias, msm_cat=msm_cat)
        self.add_array_dimensions(group=self, dim_map=self.world.attrs['dim_map'])
        zarr.consolidate_metadata(export_store)
        logger.success(f"successfully exported {self.attrs['mission']}")

    def export_to_nc(self,outname=None):
        if outname is None:
            name = self.attrs['mission']
        else:
            name = outname
        logger.info(f"exporting mission {self.attrs['mission']} to {name}.nc")
        ds = xr.open_zarr(store=self.store)
        ds.to_netcdf(f"{name}.nc")
        logger.success(f"successfully exported {self.attrs['mission']} as netcdf file")

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

    def create_dim_map(self, cmems_alias, msm_cat):
        """
        Creates a dimension mapping dictionary and updates the relevant attribute in the world group. This attribute is
        required to enable Xarray to read the zarr groups of the campaign object.
        Args:
            cmems_alias: dictionary of cmems aliases
            msm_cat: msm intake catalog

        Returns:
            void: updates the dim_map attribute of the world zarr group
        """
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
        dim_map = {}
        for k2, v2 in self.payload.items():
            dim_map[f"{self.attrs['mission']}/payload/{k2}"] = ['time']
        for k3, v3 in self.trajectory.items():
            dim_map[f"{self.attrs['mission']}/trajectory/{k3}"] = ['time']
        for k4, v4 in self.world.items():
            split_key = k4.split('_')
            for k5, v5 in v4.items():
                if split_key[0] == "cmems":
                    if [k5] in cmems_alias.values():
                        dim_map[f"{self.attrs['mission']}/world/{k4}/{k5}"] = ['time', 'depth', 'latitude', 'longitude']
                elif split_key[0] == "msm":
                    msm_metadata = msm_cat[k4].describe()['metadata']
                    msm_alias = msm_metadata.get('aliases', [])
                    if k5 in msm_alias.keys():
                        dim_map[f"{self.attrs['mission']}/world/{k4}/{k5}"] = ['time_counter', 'deptht', 'latitude',
                                                                               'longitude']
                else:
                    logger.error(f"unknown model source key {k5}")
                    raise UnknownSourceKey
        self.world.attrs.update({"dim_map": dim_map})

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
