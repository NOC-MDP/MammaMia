import os
import pickle
from dataclasses import dataclass,field
import zarr
import numpy as np
import xarray as xr
import pyinterp
import pyinterp.backends.xarray
from loguru import logger
import xesmf as xe
import blosc

from mamma_mia.exceptions import UnknownSourceKey


@dataclass
class Interpolators:
    interpolator: dict = field(default_factory=dict)
    cache: bool = False

    def build(self,worlds,mission:str) -> ():
        """
        Creates a 4D interpolator for each sensor that allows a world to be interpolated on to a trajectory

        Args:
            mission:
            worlds (zarr.Group): a zarr group containing all the world data that has been downloaded

        Returns:
            void: Interpolator object has been populated with interpolators for each variable in the world group

        """
        # for every dataset
        interpolator_priorities = worlds.attributes.interpolator_priorities
        catalog_priorities = worlds.attributes.catalog_priorities
        for key in worlds.worlds.keys():
            logger.info(f"building worlds for dataset {key}")
            # for every variable
            for var in worlds.worlds[key]:
                # for each item in matched dictionary
                world_attrs = worlds.attributes.matched_worlds[key]
                if var in world_attrs.variable_alias.keys():
                    logger.info(f"building world for variable {var}")
                    # check priorities of dataset to see if it should update the interpolated world or not
                    if self.check_priorities(key=world_attrs.variable_alias[var],
                                             source=world_attrs.source.name,
                                             worlds=worlds):
                        continue
                    if self.cache:
                        logger.info(f"getting world for variable {var} for source {world_attrs['source']} from cache")
                        imported = self.import_interp(key=world_attrs.variable_alias[var],
                                                      source=world_attrs.source.name,
                                                      mission=mission
                                                      )
                        interpolator_priorities[world_attrs.variable_alias[var]] = world_attrs.catalog_priorities[world_attrs["source"]]
                    else:
                        imported = False
                    if not imported:
                        if world_attrs.source.name == "msm":
                            pass
                            # # rename time and depth dimensions to be consistent
                            # ds = xr.open_zarr(store=worlds.attrs["zarr_stores"][key])
                            # ds = ds.rename({"deptht": "depth", "time_counter": "time"})
                            # lat = ds['nav_lat']
                            # lon = ds['nav_lon']
                            # # Define a regular grid with 1D lat/lon arrays
                            # target_lat = np.linspace(lat.min(), lat.max(), 96)
                            # target_lon = np.linspace(lon.min(), lon.max(), 67)
                            # # Create a target grid dataset
                            # target_grid = xr.Dataset({
                            #     'latitude': (['latitude'], target_lat),
                            #     'longitude': (['longitude'], target_lon)
                            # })
                            # # Create a regridder object to go from curvilinear to regular grid
                            # regridder = xe.Regridder(ds, target_grid, method='bilinear',ignore_degenerate=True)
                            # # Regrid the entire dataset
                            # ds_regridded = regridder(ds)
                            # # Add units to latitude and longitude coordinates
                            # ds_regridded['latitude'].attrs['units'] = 'degrees_north'
                            # ds_regridded['longitude'].attrs['units'] = 'degrees_east'
                            # # Convert all float32 variables in the dataset to float64
                            # ds_regridded = ds_regridded.astype('float64')
                            # ds_regridded['time'] = ds_regridded['time'].astype('datetime64[ns]')
                            # self.interpolator[world_attrs["data_id"]] = pyinterp.backends.xarray.Grid4D(ds_regridded[var], geodetic=True)
                            # if self.cache:
                            #     self.export_interp(key=world_attrs["variable_alias"][var],source="msm",mission=mission)
                            # # create or update priorities of interpolator datasetsc
                            # interpolator_priorities[world_attrs["data_id"]] = worlds.attrs["catalog_priorities"]["msm"]
                        elif world_attrs.source.name == "cmems":
                            world = xr.open_zarr(store=worlds.stores[key])
                            self.interpolator[world_attrs.variable_alias[var]] = pyinterp.backends.xarray.Grid4D(world[var],geodetic=True)
                            if self.cache:
                                self.export_interp(key=world_attrs["variable_alias"][var],source="cmems",mission=mission)
                            interpolator_priorities[world_attrs.variable_alias[var]] = catalog_priorities["cmems"]
                        else:
                            logger.error(f"unknown model source key {world_attrs.source.name}")
                            raise UnknownSourceKey

                        logger.info(f"built {var} from source {world_attrs.source.name} into interpolator: {world_attrs.variable_alias[var]}")
        worlds.attributes.interpolator_priorities = interpolator_priorities
        logger.success("interpolators built successfully")

    def import_interp(self,key:str,source: str,mission:str):
        if not os.path.isdir(f"interpolator_cache/{mission}"):
            return False
        import_loc = f"interpolator_cache/{mission}/{source}_{key}.lerp"
        if os.path.exists(import_loc):
            with open(import_loc, 'rb') as f:
                compressed_pickle = f.read()
            depressed_pickle = blosc.decompress(compressed_pickle)
            self.interpolator[key] = pickle.loads(depressed_pickle)
            logger.info(f"imported interpolator for {key} from source {source} for {mission}")
            return True
        else:
            logger.info(f"interpolator {key} not found for source {source} for {mission}")
            return False

    def export_interp(self,key:str,source:str,mission:str):
        if not os.path.isdir(f"interpolator_cache/{mission}"):
            os.mkdir(f"interpolator_cache")
            os.mkdir(f"interpolator_cache/{mission}")
        pickled_data = pickle.dumps(self.interpolator[key])
        compressed_pickle = blosc.compress(pickled_data)
        with open(f"interpolator_cache/{mission}/{source}_{key}.lerp", 'wb') as f:
            f.write(compressed_pickle)
        logger.info(f"exported interpolator {key} for source {source} for {mission}")

    @staticmethod
    def check_priorities(key:str, source:str, worlds) -> bool:
        """
        Function to check the priority of data that will be interpolated, if an existing interpolator is already present
        Args:
            key: sensor/data type
            source: world data source e.g. cmems or msm
            worlds: zarr group containing all the world data that has been downloaded

        Returns:
            bool: determines priority of data to be interpolated, if data is a higher priority then replace
                  interpolator, if of a lower priority then do not replace
        """
        if source not in ["msm", "cmems"]:
            logger.error(f"unknown model source: {source}")
            raise UnknownSourceKey
        if key in worlds.attributes.interpolator_priorities:
            logger.info(f"reality parameter {key} already exists, checking priority of data source with existing dataset")
            if  worlds.attributes.interpolator_priorities[key] > worlds.attributes.catalog_priorities["source"]:
                logger.info(f"data source {source} is a lower priority, skipping world build")
                return True
            logger.info(f"data source {source} is a higher priority, updating world build")
        return False