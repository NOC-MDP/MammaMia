import numpy as np
import plotly.graph_objects as go
import xarray as xr
from mamma_mia.auv import AUV
from dataclasses import dataclass,fields
import uuid
from loguru import logger
import zarr
from mamma_mia.catalog import Cats
from mamma_mia.interpolator import Interpolators
from mamma_mia.find_worlds import find_worlds
from mamma_mia.get_worlds import get_worlds

@dataclass
class Mission(zarr.Group):
    """
    Mission object, this contains all the components to be able to fly an AUV mission (generate interpolated data)

    Args:
        name: name of the mission
        description: description of the mission
        auv: AUV object created from AUV class
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
                 auv:AUV,
                 trajectory_path:str,
                 store=None,
                 overwrite=False,
                 excess_space: int=0.5,
                 excess_depth: int = 100,
                 msm_priority: int = 2,
                 cmems_priority: int = 1,
                 ):
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        self.attrs["name"] = name
        self.attrs["uuid"] = str(uuid.uuid4())
        self.attrs["description"] = description

        auv_exp = self.create_group("auv")
        auv_exp.attrs["id"] = auv.id
        auv_exp.attrs["type"] = auv.type.type
        auv_exp.attrs["uuid"] = str(auv.uuid)
        auv_exp.attrs["sensor_arrays"] = str(auv.sensor_arrays)

        ds = xr.open_dataset(trajectory_path)
        traj = self.create_group("trajectory")
        traj.array(name="latitudes",data=np.array(ds["m_lat"]))
        traj.array(name="longitudes",data=np.array(ds["m_lon"]))
        traj.array(name="depths",data=np.array(ds["m_depth"]))
        traj.array(name="datetimes",data=np.array(ds["time"],dtype='datetime64'))

        for i in range(traj.longitudes.__len__()):
            traj.longitudes[i] = self.__convert_to_decimal(traj.longitudes[i])
        for i in range(traj.latitudes.__len__()):
            traj.latitudes[i] = self.__convert_to_decimal(traj.latitudes[i])

        real_grp = self.create_group("reality")
        # construct sensor array dictionary to save as attribute and empty reality arrays for each sensor
        # TODO be able to handle more than one of the same array type e.g. CTD will overwrite any existing CTD arrays
        sensor_arrays = {}
        for group in auv.sensor_arrays.values():
            sensor_arrays[group.array] = {}
            for sensor in fields(group):
                # filter out uuid field
                if "uuid" in sensor.name:
                    sensor_arrays[group.array][sensor.name] = {"uuid": str(sensor.default)}
                # if field starts with sensor then it's a sensor!
                if "sensor" in sensor.name:
                    # map sensor class to a JSON serializable object (a dict basically)
                    sensor_arrays[group.array][sensor.name] = {"type":sensor.default.type,"units":sensor.default.units}
                    real_grp.full(name=sensor.default.type, shape=traj.latitudes.__len__(), dtype=np.float64, fill_value=np.nan)
                    real_grp.attrs["mapped_name"] = sensor.default.type
        # update sensor array attribute in zarr group
        self.auv.attrs.update({"sensor_arrays": sensor_arrays})
        worlds = self.create_group("world")
        extent = {
                    "max_lat": np.around(np.max(traj.latitudes),2) + excess_space,
                    "min_lat": np.around(np.min(traj.latitudes), 2) - excess_space,
                    "max_lng": np.around(np.max(traj.longitudes), 2) + excess_space,
                    "min_lng": np.around(np.min(traj.longitudes), 2) - excess_space,
            # TODO dynamically set the +/- delta on start and end time based on time step of model (need at least two time steps)
                    "start_time": np.datetime_as_string(traj.datetimes[0] - np.timedelta64(30, 'D'), unit="D"),
                    "end_time" : np.datetime_as_string(traj.datetimes[-1] + np.timedelta64(30, 'D'), unit="D"),
                    "max_depth": np.around(np.max(traj.depths), 2) + excess_depth
        }
        worlds.attrs["extent"] = extent
        worlds.attrs["catalog_priorities"] = {"msm":msm_priority,"cmems":cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}

    def build_mission(self,cat:Cats) -> ():
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
            interpolator: Interpolator object with intepolators to fly through

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

    def show_reality(self, parameter:str,colour_scale:str="Jet"):
        """
        Created an interactive plot of the auv trajectory with the given parameters data mapped onto it using the
        specified colour map.
        Args:
            parameter: parameter or sensor to visualise
            colour_scale: (optional) colour scale to use when plotting data onto trajectory

        Returns:
            interactive plotly figure that opens in a web browser.

        """
        logger.info(f"showing reality for parameter {parameter}")
        marker = {
            "size": 2,
            "color": self.reality[parameter],
            "colorscale": colour_scale,
            "opacity": 0.8,
            "colorbar": {"thickness": 40}
        }
        title = {
            "text": f"Glider Reality: {parameter}",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper"
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }
        fig = go.Figure(data=[
            go.Scatter3d(x=self.trajectory["longitudes"],
                         y=self.trajectory["latitudes"],
                         z=self.trajectory["depths"],
                         mode='markers',
                         marker=marker),
            # TODO implement bathy surface plot
            #go.Surface()
        ])

        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()
        logger.success(f"successfully plotted reality for parameter {parameter}")

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

    def export(self, store: zarr.DirectoryStore = None) -> ():
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
        logger.success(f"successfully exported {self.attrs['name']}")

    # From: https://github.com/smerckel/latlon/blob/main/latlon/latlon.py
    # Lucas Merckelbach
    @staticmethod
    def __convert_to_decimal(x):
        """
        Converts a latitiude or longitude in NMEA format to decimale degrees
        """
        sign = np.sign(x)
        x_abs = np.abs(x)
        degrees = np.floor(x_abs / 100.)
        minutes = x_abs - degrees * 100
        decimal_format = degrees + minutes / 60.
        return decimal_format * sign










