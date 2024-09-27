import uuid
from dataclasses import dataclass, InitVar,field
import numpy as np
import plotly.graph_objects as go
from loguru import logger
import pyinterp
from datetime import datetime
import os
from mamma_mia.cmems_alias import alias
import xesmf as xe
from mamma_mia.auv import AUV
import pyinterp.backends.xarray
import zarr
import xarray as xr
import intake
import copernicusmarine

@dataclass
class Cats:
    """
    Catalog class
    """
    cmems_cat: dict = field(init=False)
    msm_cat: intake.Catalog = field(init=False)
    search : InitVar[str] = "Global"
    cat_path: InitVar[str] = "https://noc-msm-o.s3-ext.jc.rl.ac.uk/mamma-mia/catalog/catalog.yml"
    overwrite: bool = False
    # TODO add in some kind of update check so that the json file is updated periodically
    # TODO need some kind of refresh option that will delete caches of downloaded data. (user enabled and probably if data is older than x?)
    def __post_init__(self, search,cat_path ):
        self.cmems_cat = copernicusmarine.describe(contains=[search], include_datasets=True,
                                                   overwrite_metadata_cache=self.overwrite)
        self.msm_cat = intake.open_catalog(cat_path)

@dataclass
class Interpolators:
    interpolator: dict = field(default_factory=dict)

    def build(self,worlds:zarr.Group):
        """
        Creates a 4D interpolator that allows a world to be interpolated on to a trajectory

        Parameters:
        - None

        Returns:
        - World object with an interpolator
        """
        # for every dataset
        for key in worlds.keys():
            logger.info(f"building worlds for dataset {key}")
            # for every variable
            for var in worlds[key]:
                logger.info(f"building world for variable {var}")
                # for each item in matched dictionary
                for k1, v1, in worlds.attrs["matched_worlds"][key].items():
                    # if variable names match (this is to ensure variable names are consistent)
                    if var == v1:
                        split_key = key.split("_")
                        if split_key[0] == "msm":
                            if self.__check_priorities(key=k1, source="msm",worlds=worlds):
                                continue
                            # rename time and depth dimensions to be consistent
                            ds = xr.open_zarr(store=worlds.attrs["zarr_stores"][key])
                            ds.rename({"deptht": "depth", "time_counter": "time"})
                            lat = ds['nav_lat']
                            lon = ds['nav_lon']
                            # Define a regular grid with 1D lat/lon arrays
                            target_lat = np.linspace(lat.min(), lat.max(), 20)
                            target_lon = np.linspace(lon.min(), lon.max(), 14)
                            # Create a target grid dataset
                            target_grid = xr.Dataset({
                                'latitude': (['latitude'], target_lat),
                                'longitude': (['longitude'], target_lon)
                            })
                            # Create a regridder object to go from curvilinear to regular grid
                            regridder = xe.Regridder(ds, target_grid, method='bilinear')
                            # Regrid the entire dataset
                            ds_regridded = regridder(ds)
                            # Add units to latitude and longitude coordinates
                            ds_regridded['latitude'].attrs['units'] = 'degrees_north'
                            ds_regridded['longitude'].attrs['units'] = 'degrees_east'
                            # Convert all float32 variables in the dataset to float64
                            ds_regridded = ds_regridded.astype('float64')
                            ds_regridded['time'] = ds_regridded['time'].astype('datetime64[ns]')
                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(ds_regridded, geodetic=True)
                            # create or update priorities of interpolator datasetsc
                            worlds.attrs["interpolator_priorities"][k1] = \
                            worlds.attrs["catalog_priorities"]["msm"]
                        elif split_key[0] == "cmems":
                            if self.__check_priorities(key=k1, source="cmems",worlds=worlds):
                                continue
                            world = xr.open_zarr(store=worlds.attrs["zarr_stores"][key])
                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(world[var],geodetic=True)
                            worlds.attrs["interpolator_priorities"][k1] = worlds.attrs["catalog_priorities"]["cmems"]
                        else:
                            logger.error("unknown model source key")
                            raise Exception
                        logger.info(f"built {var} from source {split_key[0]} into interpolator: {k1}")
        logger.success("interpolators built successfully")

    @staticmethod
    def __check_priorities(key:str, source:str, worlds:zarr.Group) -> bool:
        if source not in ["msm", "cmems"]:
            logger.error(f"unknown source: {source}")
            raise Exception
        if key in worlds.attrs["interpolator_priorities"]:
            logger.warning(f"reality parameter {key} already exists, checking priority of data source with existing dataset")
            if worlds.attrs["interpolator_priorities"][key] > worlds.attrs["catalog_priorities"][source]:
                logger.info(f"data source {source} is a lower priority, skipping world build")
                return True
            logger.info(f"data source {source} is a higher priority, updating world build")
        return False

@dataclass
class Mission(zarr.Group):
    """
    Creates a mamma_mia object

    Parameters:
    - id
    - description
    - world
    - trajectory
    - glider
    -reality

    Returns:
    - Mission object that is ready for flight!
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
        self.attrs["id"] = str(uuid.uuid4())
        self.attrs["description"] = description

        auv_exp = self.create_group("auv")
        auv_exp.attrs["id"] = auv.id
        auv_exp.attrs["type"] = auv.type
        auv_exp.attrs["sensor_suite"] = auv.sensor_suite.to_dict()

        ds = xr.open_dataset(trajectory_path)
        traj = self.create_group("trajectory")
        traj.array(name="latitudes",data=np.array(ds["m_lat"]))
        traj.array(name="longitudes",data=np.array(ds["m_lon"]))
        traj.array(name="depths",data=np.array(ds["m_depth"]))
        traj.array(name="datetimes",data=np.array(ds["time"],dtype='datetime64'))

        for i in range(traj.longitudes.__len__()):
            traj.longitudes[i] = self.__convertToDecimal(traj.longitudes[i])
        for i in range(traj.latitudes.__len__()):
            traj.latitudes[i] = self.__convertToDecimal(traj.latitudes[i])

        real_grp = self.create_group("reality")
        for group in auv.sensor_suite.values():
            for sensor in group.sensors.values():
                real_grp.full(name=sensor.type, shape=traj.latitudes.__len__(), dtype=np.float64, fill_value=np.nan)
                real_grp.attrs["mapped_name"] = sensor.type

        worlds = self.create_group("world")
        extent = {
                    "max_lat": np.around(np.max(traj.latitudes),2) + excess_space,
                    "min_lat": np.around(np.min(traj.latitudes), 2) - excess_space,
                    "max_lng": np.around(np.max(traj.longitudes), 2) + excess_space,
                    "min_lng": np.around(np.min(traj.longitudes), 2) - excess_space,
                    "start_time": np.datetime_as_string(traj.datetimes[0] - np.timedelta64(30, 'D'), unit="D"),
                    "end_time" : np.datetime_as_string(traj.datetimes[-1] + np.timedelta64(30, 'D'), unit="D"),
                    "max_depth": np.around(np.max(traj.latitudes), 2) + excess_depth
        }
        worlds.attrs["extent"] = extent
        worlds.attrs["catalog_priorities"] = {"msm":msm_priority,"cmems":cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}

    def build_mission(self,cat:Cats) -> ():
        self.__find_worlds(cat=cat)
        zarr_stores = {}
        for key, value in self.world.attrs["matched_worlds"].items():
            self.__get_worlds(key=key, value=value,cat=cat, zarr_stores=zarr_stores)
        self.world.attrs.update({"zarr_stores": zarr_stores})

    def fly(self,interpol:Interpolators):
        logger.info(f"flying {self.name} using {self.auv.attrs['id']}")
        flight = {
            "longitude": np.array(self.trajectory["longitudes"]),
            "latitude": np.array(self.trajectory["latitudes"]),
            "depth": np.array(self.trajectory["depths"]),
            "time": np.array(self.trajectory["datetimes"], dtype='datetime64'),
        }
        for key in self.reality.array_keys():
            try:
                logger.info(f"flying through {key} world and creating reality")
                self.reality[key] = interpol.interpolator[key].quadrivariate(flight)
            except KeyError:
                logger.warning(f"no interpolator found for parameter {key}")

        logger.success(f"{self.name} flown successfully")

    def show_reality(self, parameter:str,colourscale:str="Jet"):
        logger.info(f"showing reality for parameter {parameter}")
        marker = {
            "size": 2,
            "color": self.reality[parameter],
            "colorscale": colourscale,
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

    def export(self) -> ():
        logger.info(f"exporting mission {self.name} to {self.name}.zarr")

        export_store = zarr.DirectoryStore(f"{self.name}.zarr")
        zarr.copy_store(self.store, export_store)

        logger.success(f"successfully exported {self.name}")

    def plot_trajectory(self,colourscale:str='Viridis',):
        """
        Creates a plotly figure of the Trajectory object.

        Parameters:
        None

        Returns:
        - Plotly figure of the Trajectory object. (This will open in a web browser)
        """
        marker = {
            "size": 2,
            "color": np.array(self.trajectory.datetimes).tolist(),
            "colorscale": colourscale,
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
            data=[go.Scatter3d(x=self.longitudes, y=self.latitudes, z=self.depths, mode='markers', marker=marker)])
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()

    # From: https://github.com/smerckel/latlon/blob/main/latlon/latlon.py
    # Lucas Merckelbach
    @staticmethod
    def __convertToDecimal(x):
        """
        Converts a latitiude or longitude in NMEA format to decimale degrees
        """
        sign = np.sign(x)
        xAbs = np.abs(x)
        degrees = np.floor(xAbs / 100.)
        minutes = xAbs - degrees * 100
        decimalFormat = degrees + minutes / 60.
        return decimalFormat * sign

    def __find_worlds(self,cat:Cats):
        """
        Finds a world that matches the reality required.

        Parameters:
        - reality: Reality object containing the empty reality the world needs to match

        Returns:
        - Python dict with matched dataset ids and variable names

        Notes:
        This is a wrapper function around specific find world functions e.g. CMEMS or Jasmin
        """
        # for every array in the reality group
        matched_worlds = {}
        for key in self.reality.array_keys():
            logger.info(f"searching worlds for key {key}")
            matched_worlds = self.__find_cmems_worlds(key=key,cat=cat,matched_worlds=matched_worlds)
            matched_worlds = self.__find_msm_worlds(key=key,cat=cat,matched_worlds=matched_worlds)
        self.world.attrs.update({"matched_worlds": matched_worlds})
        logger.success("world search completed successfully")


    def __get_worlds(self, key, value,cat:Cats,zarr_stores:dict):
        """
        Gets a matched world from its respective source

        Parameters:
        - key: string that represents the world id
        - value: dictionary of variables to subset from world

        Returns:
        - zarr store: string that denotes where the zarr store holding the world has been saved.

        Notes:
        This is a wrapper function around specific get world functions e.g. CMEMS or Jasmin
        """
        split_key = key.split("_")

        if split_key[0] == "cmems":
            zarr_store = self.__get_cmems_worlds(key=key, value=value)
            zarr_stores[key] = zarr_store
        elif split_key[0] == "msm":
            zarr_store = self.__get_msm_worlds(key=key, value=value,catalog=cat)
            zarr_stores[key] = zarr_store
        else:
            logger.error("unknown model source key")
            raise Exception
        dest_group = self.create_group(f"world/{key}")
        zarr_source = zarr.open(zarr_store, mode='r')
        zarr.copy_all(source=zarr_source, dest=dest_group)

        return zarr_store

    def __find_msm_worlds(self,key:str,cat:Cats,matched_worlds:dict) -> dict:
        """

        Args:
            key: string that represents the variable to find

        Returns:
            matched worlds dictionary containing dataset ids and variable names

        """
        for k1,v1 in cat.msm_cat.items():
            var_key = None
            logger.info(f"searching {k1}")
            metadata = v1.describe()['metadata']
            aliases = metadata.get('aliases', [])
            # check if the key is in one of the variables alias dictionaries
            for k2,v2 in aliases.items():
                if key in v2:
                    var_key = k2
            spatial_extent = metadata.get('spatial_extent', [])
            temporal_extent = metadata.get('temporal_extent', [])
            start_traj = float((np.datetime64(self.world.attrs["extent"]["start_time"]) - np.datetime64(
                '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
            end_traj = float((np.datetime64(self.world.attrs["extent"]["end_time"]) - np.datetime64(
                '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
            if temporal_extent:
                start_datetime = datetime.fromisoformat(temporal_extent[0].replace("Z", "+00:00")).timestamp()*1000
                end_datetime = datetime.fromisoformat(temporal_extent[1].replace("Z", "+00:00")).timestamp()*1000
                # Check if the item is within the desired date range and spatial bounds
                if (spatial_extent and
                        self.world.attrs["extent"]["min_lat"] >= spatial_extent[0] and self.world.attrs["extent"]["max_lat"] <= spatial_extent[2] and
                        self.world.attrs["extent"]["min_lng"] >= spatial_extent[1] and self.world.attrs["extent"]["max_lng"] <= spatial_extent[3] and
                        start_traj >= start_datetime and end_traj <= end_datetime and var_key is not None):
                    logger.success(f"found a match in {k1} for {key}")
                    if k1 in matched_worlds:
                        logger.info(f"updating {k1} with key {key}")
                        matched_worlds[k1][key] = var_key
                    else:
                        logger.info(f"creating new matched world {k1} for key {key}")
                        matched_worlds[k1] = {key: var_key}
        return matched_worlds

    def __find_cmems_worlds(self, key: str,cat:Cats,matched_worlds:dict) -> dict:
        """
        Traverses CMEMS catalog and find products/datasets that match the glider sensors and
        the trajectory spatial and temporal extent.

        Parameters:
        - key: string that represents the variable to find

        Returns:
        - matched worlds dictionary containing dataset ids and variable names that reside within it.
        """
        for k1, v1 in cat.cmems_cat.items():
            logger.info(f"searching cmems {k1}")
            for i in range(len(v1)):
                # ensure it is a numerical model
                if v1[i]["sources"][0] != "Numerical models":
                    logger.warning(f"{v1[i]['sources'][0]} is not a numerical model")
                    continue
                # check each dataset
                for j in range(len(v1[i]["datasets"])):
                    dataset = v1[i]["datasets"][j]
                    k = None
                    for k in range(len(dataset["versions"][0]["parts"][0]["services"])):
                        if dataset["versions"][0]["parts"][0]["services"][k]["service_format"] == "zarr" and \
                                dataset["versions"][0]["parts"][0]["services"][k]["service_type"][
                                    "service_name"] == "arco-geo-series":
                            break
                    variables = dataset["versions"][0]["parts"][0]["services"][k]["variables"]
                    # check each variable
                    for m in range(len(variables)):
                        if key not in alias:
                            print(f"variable {key} not in alias file")
                        if variables[m]["short_name"] in alias[key]:
                            # if trajectory spatial extent is within variable data
                            if (variables[m]["bbox"][0] < self.world.attrs["extent"]["min_lng"] or
                                    variables[m]["bbox"][1] > self.world.attrs["extent"]["min_lat"]
                                    or variables[m]["bbox"][2] > self.world.attrs["extent"]["max_lng"] or
                                    variables[m]["bbox"][3] > self.world.attrs["extent"]["min_lat"]):
                                # find the time coordinate index
                                n = None
                                for n in range(len(variables[m]["coordinates"])):
                                    if variables[m]["coordinates"][n]["coordinates_id"] == "time":
                                        break
                                # get time values either as part of values list or as a specific max and min value
                                # both are possibilities it seems!
                                try:
                                    start = variables[m]["coordinates"][n]["values"][0]
                                    end = variables[m]["coordinates"][n]["values"][-1]
                                    step = variables[m]["coordinates"][n]["values"][1] - \
                                           variables[m]["coordinates"][n]["values"][0]
                                except TypeError:
                                    start = variables[m]["coordinates"][n]["minimum_value"]
                                    end = variables[m]["coordinates"][n]["maximum_value"]
                                    step = variables[m]["coordinates"][n]["step"]
                                # convert trajectory datetimes into timestamps to be able to compare with CMEMS catalog
                                start_traj = float((np.datetime64(self.world.attrs["extent"]["start_time"]) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                end_traj = float((np.datetime64(self.world.attrs["extent"]["end_time"]) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                # check if trajectory temporal extent is within variable data
                                if start_traj > start and end_traj < end:
                                    # make sure data is at least daily
                                    if step <= 86400000:
                                        logger.success(f"found a match in {dataset['dataset_id']} for {key}")
                                        if dataset["dataset_id"] in matched_worlds:
                                            logger.info(f"updating {dataset['dataset_id']} with key {key}")
                                            matched_worlds[dataset["dataset_id"]][key] = variables[m]["short_name"]
                                        else:
                                            logger.info(f"creating new matched world {dataset['dataset_id']} for key {key}")
                                            matched_worlds[dataset["dataset_id"]] = {key: variables[m]["short_name"]}
        return matched_worlds

    def __get_msm_worlds(self,key: str,value,catalog:Cats):
        """

        Args:
            key: string the represents the source name
            value: object that contains the intake entry of the matched dataset

        Returns:
            string that represents the zarr store location of the downloaded data
        """
        var_str = ""
        vars2 = []
        msm = self.create_group(key)
        msm.attrs["spatial_extent"] = {"max_lng": self.world.attrs["extent"]["max_lng"],
                                         "min_lng": self.world.attrs["extent"]["min_lng"],
                                         "max_lat": self.world.attrs["extent"]["max_lat"],
                                         "min_lat": self.world.attrs["extent"]["min_lat"],
                                         "max_depth": self.world.attrs["extent"]["max_depth"]}
        msm.attrs["temporal_extent"] = {"start_time": self.world.attrs["extent"]["start_time"],
                                          "end_time": self.world.attrs["extent"]["end_time"]}


        for k2,v2 in value.items():
            vars2.append(v2)
            var_str = var_str+str(v2)+"_"
        # TODO add in a min depth parameter? or always assume its the surface?
        zarr_f = (f"{key}_{var_str}_{msm.attrs['spatial_extent']['max_lng']}_{msm.attrs['spatial_extent']['min_lng']}_"
                  f"{msm.attrs['spatial_extent']['max_lat']}_{msm.attrs['spatial_extent']['min_lat']}_"
                  f"{msm.attrs['spatial_extent']['max_depth']}_{msm.attrs['temporal_extent']['start_time']}_"
                  f"{msm.attrs['temporal_extent']['end_time']}.zarr")
        zarr_d = "msm-data/"
        logger.info(f"getting msm world {zarr_f}")
        if not os.path.isdir(zarr_d + zarr_f):
            logger.info(f"{zarr_f} has not been cached, downloading now")
            data = catalog.msm_cat[str(key)].to_dask()
            # Assuming ds is your dataset, and lat/lon are 2D arrays with dimensions (y, x)
            lat = data['nav_lat']  # 2D latitude array (y, x)
            lon = data['nav_lon']  # 2D longitude array (y, x)
            # Step 1: Flatten lat/lon arrays and get the x, y indices
            lat_flat = lat.values.flatten()
            lon_flat = lon.values.flatten()
            # Step 2: Calculate the squared Euclidean distance for each point on the grid
            distance = np.sqrt((lat_flat - msm.attrs['spatial_extent']['max_lat']) ** 2 + (lon_flat - msm.attrs['spatial_extent']['max_lng']) ** 2)
            distance2 = np.sqrt((lat_flat - msm.attrs['spatial_extent']['min_lat']) ** 2 + (lon_flat - msm.attrs['spatial_extent']['min_lng']) ** 2)
            # Step 3: Find the index of the minimum distance
            min_index = np.argmin(distance)
            min_index2 = np.argmin(distance2)
            # Step 4: Convert the flattened index back to 2D indices
            y_size, x_size = lat.shape  # Get the shape of the 2D grid
            y_index_max, x_index_max = np.unravel_index(min_index, (y_size, x_size))
            y_index_min, x_index_min = np.unravel_index(min_index2, (y_size, x_size))
            subset = data[vars2].sel(y=slice(y_index_min,y_index_max),
                                     x=slice(x_index_min,x_index_max),
                                     deptht=slice(0,msm.attrs['spatial_extent']['max_depth']),
                                     time_counter=slice(msm.attrs['temporal_extent']['start_time'],msm.attrs['temporal_extent']['end_time']))
            subset.to_zarr(store=zarr_d + zarr_f,safe_chunks=False)
            logger.success(f"{zarr_f} has been cached")
        return zarr_d + zarr_f

    def __get_cmems_worlds(self, key, value):
        """
        Checks for the presence of, or downloads if not present the required subset of CMEMS catalog

        Parameters
        - key: string that represents the cmems dataset id
        - value: dictionary that contains the variable names to download

        Returns:
        string that represents the zarr store location of the downloaded data

        """

        vars2 = []
        # pull out the var names that CMEMS needs NOTE not the same as Mamma Mia uses
        for k2, v2 in value.items():
            vars2.append(v2)
        cmems = self.create_group(key)
        cmems.attrs["spatial_extent"] = {"max_lng": self.world.attrs["extent"]["max_lng"],
                                         "min_lng": self.world.attrs["extent"]["min_lng"],
                                         "max_lat": self.world.attrs["extent"]["max_lat"],
                                         "min_lat": self.world.attrs["extent"]["min_lat"],
                                         "max_depth": self.world.attrs["extent"]["max_depth"]}
        cmems.attrs["temporal_extent"] = {"start_time": self.world.attrs["extent"]["start_time"],
                                          "end_time": self.world.attrs["extent"]["end_time"]}

        zarr_f = (f"{key}_{cmems.attrs['spatial_extent']['max_lng']}_{cmems.attrs['spatial_extent']['min_lng']}_"
                  f"{cmems.attrs['spatial_extent']['max_lat']}_{cmems.attrs['spatial_extent']['min_lat']}_"
                  f"{cmems.attrs['spatial_extent']['max_depth']}_{cmems.attrs['temporal_extent']['start_time']}_"
                  f"{cmems.attrs['temporal_extent']['end_time']}.zarr")
        zarr_d = "copernicus-data/"
        logger.info(f"getting cmems world {zarr_f}")
        if not os.path.isdir(zarr_d + zarr_f):
            logger.info(f"{zarr_f} has not been cached, downloading now")
            copernicusmarine.subset(
                dataset_id=key,
                variables=vars2,
                minimum_longitude=cmems.attrs['spatial_extent']['min_lng'],
                maximum_longitude=cmems.attrs['spatial_extent']['max_lng'],
                minimum_latitude=cmems.attrs['spatial_extent']['min_lat'],
                maximum_latitude=cmems.attrs['spatial_extent']['max_lat'],
                start_datetime=str(cmems.attrs['temporal_extent']['start_time']),
                end_datetime=str(cmems.attrs['temporal_extent']['end_time']),
                minimum_depth=0,
                maximum_depth=cmems.attrs['spatial_extent']['max_depth'],
                output_filename=zarr_f,
                output_directory=zarr_d,
                file_format="zarr",
                force_download=True
            )
            logger.success(f"{zarr_f} has been cached")
        return zarr_d + zarr_f
