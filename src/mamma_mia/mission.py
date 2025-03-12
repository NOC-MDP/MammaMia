import numpy as np
import plotly.graph_objects as go
import xarray as xr
from cattrs import unstructure
from mamma_mia import Platform
from attrs import define
import uuid
from loguru import logger
import zarr
from mamma_mia.catalog import Cats
from mamma_mia.interpolator import Interpolators
from mamma_mia.find_worlds import find_worlds
from mamma_mia.get_worlds import get_worlds
from mamma_mia.exceptions import UnknownSourceKey, CriticalParameterMissing


@define
class Mission(zarr.Group):
    """
    Mission object, this contains all the components to be able to fly an AUV mission (generate interpolated data)

    Args:
        name: name of the mission
        description: description of the mission
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
                 name:str,
                 description:str,
                 platform:Platform,
                 trajectory_path:str,
                 store=None,
                 overwrite=False,
                 excess_space: int=0.5,
                 extra_depth: int = 100,
                 msm_priority: int = 2,
                 cmems_priority: int = 1,
                 ):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        # general mission meta data
        self.attrs["name"] = name
        self.attrs["uuid"] = str(uuid.uuid4())
        self.attrs["description"] = description

        # create platform attributes from platform class
        platform2 = self.create_group("platform")
        platform_unstruct = unstructure(platform)
        platform2.attrs.update(platform_unstruct)

        # find parameter keys
        lat_key = self.find_parameter_key(parameter="LATITUDE")
        lon_key = self.find_parameter_key(parameter="LONGITUDE")
        alt_key = self.find_parameter_key(parameter="ALTITUDE")
        pitch_key = self.find_parameter_key(parameter="PITCH")
        yaw_key = self.find_parameter_key(parameter="YAW")
        roll_key = self.find_parameter_key(parameter="ROLL")
        time_key = self.find_parameter_key(parameter="TIME")

        # create trajectory group from input simulated trajectory and sensor/parameter metadata
        ds = xr.open_dataset(trajectory_path)
        trajectory = self.create_group("trajectory")
        # TODO have a better reporting process so its clear to the user what is missing and where
        # TODO e.g. it could be a missing or malformed parameter, or sensor or missing from netcdf input.
        try:
            trajectory.array(name="latitudes",data=np.array(ds[lat_key]))
            trajectory.array(name="longitudes",data=np.array(ds[lon_key]))
            trajectory.array(name="altitude",data=np.array(ds[alt_key]))
            trajectory.array(name="datetimes",data=np.array(ds[time_key],dtype='datetime64'))
        except KeyError as e:
            logger.error(f"Critical parameter for trajectory missing: {e}")
            raise CriticalParameterMissing
        try:
            if pitch_key is not None:
                trajectory.array(name="pitch", data=np.array(ds[pitch_key]))
            else:
                logger.warning(f"Optional parameter pitch not specified in sensor")
        except KeyError as e:
            logger.warning(f"Optional pitch parameter for trajectory not found in simulated data: {e}")

        try:
            if yaw_key is not None:
                trajectory.array(name="yaw", data=np.array(ds[yaw_key]))
            else:
                logger.warning(f"Optional parameter yaw not specified in sensor")
        except KeyError as e:
            logger.warning(f"Optional yaw parameter for trajectory not found in simulated data: {e}")

        try:
            if roll_key is not None:
                trajectory.array(name="roll", data=np.array(ds[roll_key]))
            else:
                logger.warning(f"Optional parameter roll not specified in sensor")
        except KeyError as e:
            logger.warning(f"Optional roll parameter for trajectory not found in simulated data: {e}")


        # TODO this most likely will only be needed for specific simulator inputs.
        # convert from glider format to decimal degrees
        for i in range(trajectory.longitudes.__len__()):
            trajectory.longitudes[i] = self.__convert_to_decimal(trajectory.longitudes[i])
        for i in range(trajectory.latitudes.__len__()):
            trajectory.latitudes[i] = self.__convert_to_decimal(trajectory.latitudes[i])

        # create empty world group
        worlds = self.create_group("world")
        if np.around(np.min(trajectory.altitude), 2) - extra_depth < 0:
            min_altitude = 0
        else:
            min_altitude = np.around(np.min(trajectory.altitude), 2) - extra_depth
        extent = {
                    "max_lat": np.around(np.max(trajectory.latitudes),2) + excess_space,
                    "min_lat": np.around(np.min(trajectory.latitudes), 2) - excess_space,
                    "max_lng": np.around(np.max(trajectory.longitudes), 2) + excess_space,
                    "min_lng": np.around(np.min(trajectory.longitudes), 2) - excess_space,
            # TODO dynamically set the +/- delta on start and end time based on time step of model (need at least two time steps)
                    "start_time": np.datetime_as_string(trajectory.datetimes[0] - np.timedelta64(30, 'D'), unit="D"),
                    "end_time" : np.datetime_as_string(trajectory.datetimes[-1] + np.timedelta64(30, 'D'), unit="D"),
                    "min_altitude": min_altitude,
        }
        worlds.attrs["extent"] = extent
        worlds.attrs["catalog_priorities"] = {"msm":msm_priority,"cmems":cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}
        worlds.attrs["dim_map"] = {}
        
        sensors = self.create_group("sensors")


        # real_grp = self.create_group("reality")
        # real_grp.array(name="latitudes",data=np.array(ds["m_lat"]))
        # real_grp.array(name="longitudes",data=np.array(ds["m_lon"]))
        # for i in range(real_grp.longitudes.__len__()):
        #     real_grp.longitudes[i] = self.__convert_to_decimal(real_grp.longitudes[i])
        # for i in range(real_grp.latitudes.__len__()):
        #     real_grp.latitudes[i] = self.__convert_to_decimal(real_grp.latitudes[i])
        # real_grp.array(name="depths",data=np.array(ds["m_depth"]))
        # real_grp.array(name="datetimes",data=np.array(ds["time"],dtype='datetime64'))
        # real_grp.array(name="pitch", data=np.array(ds["m_pitch"]))
        # construct sensor array dictionary to save as attribute and empty reality arrays for each sensor
        # TODO be able to handle more than one of the same array type e.g. CTD will overwrite any existing CTD arrays
        sensor_arrays = {}
        # for group in auv.sensor_arrays.values():
        #     sensor_arrays[group.array] = {}
        #     for sensor in fields(group):
        #         # filter out uuid field
        #         if "uuid" in sensor.name:
        #             sensor_arrays[group.array][sensor.name] = {"uuid": str(sensor.default)}
        #         # if field starts with sensor then it's a sensor!
        #         if "sensor" in sensor.name:
        #             # map sensor class to a JSON serializable object (a dict basically)
        #             sensor_arrays[group.array][sensor.name] = {"type":sensor.default.type,"units":sensor.default.units}
        #             real_grp.full(name=sensor.default.type, shape=traj.latitudes.__len__(), dtype=np.float64, fill_value=np.nan)
        #             real_grp.attrs["mapped_name"] = sensor.default.type
        # update sensor array attribute in zarr group
        #self.auv.attrs.update({"sensor_arrays": sensor_arrays})


    def find_parameter_key(self,parameter:str,instrument_type:str ="data loggers") -> str:
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

    def build_mission(self,cat:Cats):
        """
        build missions, this searches for relevant data, downloads and updates attributes as needed
        Args:
            cat: Initialised Cats object, this contains catalogs for all source data

        Returns:
            void: Mission object is now populated with world data ready to build interpolators for. Matched worlds
                  and zarr store attributes are updated with the new values (what worlds match sensors and trajectory etc)

        """
        matched_worlds = find_worlds(cat=cat,reality=self.reality,extent=self.world.attrs["extent"])
        self.world.attrs.update({"matched_worlds": matched_worlds})
        zarr_stores = get_worlds(cat=cat, world=self.world)
        self.world.attrs.update({"zarr_stores": zarr_stores})

    def fly(self,interpolator:Interpolators):
        """

        Args:
            interpolator: Interpolator object with interpolators to fly through

        Returns:
            void: mission object with filled reality arrays of interpolated data, i.e. AUV has flown its
                  mission through the world.
        """
        logger.info(f"flying {self.attrs['name']} using {self.auv.attrs['id']}")
        flight = {
            "longitude": np.array(self.trajectory["longitudes"]),
            "latitude": np.array(self.trajectory["latitudes"]),
            "depth": np.array(self.trajectory["depths"]),
            "time": np.array(self.trajectory["datetimes"], dtype='datetime64'),
        }
        for key in self.reality.array_keys():
            try:
                logger.info(f"flying through {key} world and creating reality")
                self.reality[key] = interpolator.interpolator[key].quadrivariate(flight)
            except KeyError:
                logger.warning(f"no interpolator found for parameter {key}")

        logger.success(f"{self.attrs['name']} flown successfully")

    def show_reality(self):
        """
        Creates an interactive plot of the AUV trajectory with the given parameters data mapped onto it using the
        specified colour map.

        Returns:
            Interactive plotly figure that opens in a web browser.
        """
        # Example parameters for the dropdown
        # Example parameters and their expected value ranges (cmin and cmax)
        # TODO dynamically build this from AUV sensor array
        parameters = {
            "temperature": {"cmin": 10, "cmax": 25},
            "salinity": {"cmin": 34, "cmax": 36},
            "phosphate": {"cmin": 0, "cmax": 1},
            "silicate": {"cmin": 0, "cmax": 6}
        }

        # List of available color scales for the user to choose from
        colour_scales = ["Jet","Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

        # Initial setup: first parameter and color scale
        initial_parameter = "temperature"
        initial_colour_scale = "Jet"

        marker = {
            "size": 2,
            "color": np.array(self.reality[initial_parameter]),  # Ensuring it's serializable
            "colorscale": initial_colour_scale,
            "cmin": parameters[initial_parameter]["cmin"],  # Set the minimum value for the color scale
            "cmax": parameters[initial_parameter]["cmax"],  # Set the maximum value for the color scale
            "opacity": 0.8,
            "colorbar": {"thickness": 40}
        }

        title = {
            "text": f"Glider Reality: {initial_parameter}",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper"
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }

        # Create the initial figure
        fig = go.Figure(data=[
            go.Scatter3d(
                x=self.trajectory["longitudes"],
                y=self.trajectory["latitudes"],
                z=self.trajectory["depths"],
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
                    {"marker.color": [np.array(self.reality[parameter])],  # Update the color for the new parameter
                     "marker.cmin": parameters[parameter]["cmin"],  # Set cmin for the new parameter
                     "marker.cmax": parameters[parameter]["cmax"],  # Set cmax for the new parameter
                     "marker.colorscale": initial_colour_scale},  # Keep the initial color scale (can be updated below)
                    {"title.text": f"Glider Reality: {parameter}"}  # Update the title to reflect the new parameter
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
                dict(text="Color Scale:", x=0.05, y=1.15, showarrow=False, xref="paper", yref="paper",font=dict(size=14))
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
        logger.success(f"successfully plotted reality")

    def plot_trajectory(self,colour_scale:str='Viridis',):
        """
        Created an interactive plot of the auv trajectory, with the datetime of the trajectory colour mapped onto it.

        Args:
            colour_scale: (optional) colour scale to use when plotting datetime onto trajectory

        Returns:
            interactive plotly figure that opens in a web browser.

        """
        marker = {
            "size": 2,
            "color": np.array(self.trajectory.datetimes).tolist(),
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
            data=[go.Scatter3d(x=self.trajectory["longitudes"], y=self.trajectory["latitudes"], z=self.trajectory["depths"], mode='markers', marker=marker)])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()

    def export(self, cmems_alias, msm_cat, store: zarr.DirectoryStore = None):
        """
        Exports mission to a zarr directory store
        Args:
            store: path to save mission zarr group too.

        Returns:
            void: zarr group is saved to directory store
        """
        if store is None:
            export_store = zarr.DirectoryStore(f"{self.attrs['name']}.zarr")
        else:
            export_store = store
        logger.info(f"exporting mission {self.attrs['name']} to {export_store}")
        zarr.copy_store(self.store, export_store)
        self.create_dim_map(cmems_alias=cmems_alias,msm_cat=msm_cat)
        self.add_array_dimensions(group=self,dim_map=self.world.attrs['dim_map'])
        zarr.consolidate_metadata(export_store)
        logger.success(f"successfully exported {self.attrs['name']}")

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

    def create_dim_map(self,cmems_alias,msm_cat):
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
        for k2, v2 in self.reality.items():
            dim_map[f"{self.attrs['name']}/reality/{k2}"] = ['time']
        for k3, v3 in self.trajectory.items():
            dim_map[f"{self.attrs['name']}/trajectory/{k3}"] = ['time']
        for k4, v4 in self.world.items():
            split_key = k4.split('_')
            for k5, v5 in v4.items():
                if split_key[0] == "cmems":
                    if [k5] in cmems_alias.values():
                        dim_map[f"{self.attrs['name']}/world/{k4}/{k5}"] = ['time', 'depth', 'latitude', 'longitude']
                elif split_key[0] == "msm":
                    msm_metadata = msm_cat[k4].describe()['metadata']
                    msm_alias = msm_metadata.get('aliases', [])
                    if k5 in msm_alias.keys():
                        dim_map[f"{self.attrs['name']}/world/{k4}/{k5}"] = ['time_counter', 'deptht', 'latitude','longitude']
                else:
                    logger.error(f"unknown model source key {k5}")
                    raise UnknownSourceKey
        self.world.attrs.update({"dim_map": dim_map})


    def add_array_dimensions(self,group, dim_map, path=""):
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








