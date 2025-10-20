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
from mamma_mia.find_worlds import SourceType
from mamma_mia.worlds import WorldsConf


@dataclass
class Interpolators:
    interpolator: dict = field(default_factory=dict)
    cache: bool = False

    def build(self,worlds:WorldsConf,mission:str,source_type:SourceType) -> ():
        """
        Creates a 4D interpolator for each sensor that allows a world to be interpolated on to a trajectory

        Args:
            source_type:
            mission:
            worlds (zarr.Group): a zarr group containing all the world data that has been downloaded

        Returns:
            void: Interpolator object has been populated with interpolators for each variable in the world group

        """
        # for every dataset
        for key in worlds.worlds.keys():
            logger.info(f"building worlds for dataset {key}")
            # for every variable
            for var in worlds.worlds[key]:
                # for each item in matched dictionary
                world_attrs = worlds.attributes.matched_worlds[key]
                if var in world_attrs.variable_alias.keys():
                    logger.info(f"building world for variable {var}")
                    if self.cache:
                        logger.info(f"getting world for variable {var} for source {world_attrs['source']} from cache")
                        imported = self.import_interp(key=world_attrs.variable_alias[var],
                                                      source_type=source_type,
                                                      mission=mission
                                                      )
                    else:
                        imported = False
                    if not imported:
                        if source_type == SourceType.MSM:
                            ds = xr.open_zarr(store=worlds.stores[key])
                            # check that dimensions of lat and lon are at least larger than 1 as 1 degree models on glider scale deployments
                            # are often too low a resolution to have multiple grid cells in the mission extent.
                            if ds['nav_lat'].sizes['x'] == 1:
                                logger.warning("dataset latitude dimension length = 1, cannot interpolate, likely too low resolution")
                                continue
                            if ds['nav_lon'].sizes['x'] == 1:
                                logger.warning("dataset longitude dimension length = 1, cannot interpolate, likely too low resolution")
                                continue
                            if ds['time_counter'].sizes['time_counter'] <= 1:
                                logger.warning("dataset time dimension length = 1, cannot interpolate, likely too low resolution")
                                continue
                            # rename time and depth dimensions to be consistent
                            # depths can be named t u or v depending on their grid
                            try:
                                ds = ds.rename({"deptht": "depth", "time_counter": "time","nav_lon":"lon", "nav_lat":"lat"})
                            except ValueError:
                                try:
                                    ds = ds.rename({"depthu": "depth", "time_counter": "time","nav_lon":"lon", "nav_lat":"lat"})
                                except ValueError:
                                    ds = ds.rename({"depthv": "depth", "time_counter": "time","nav_lon":"lon", "nav_lat":"lat"})
                            lat = ds['lat']
                            lon = ds['lon']

                            # reduce arrays to get max and min values
                            latmin = lat.reduce(np.min,dim=['x','y']).values
                            latmax = lat.reduce(np.max,dim=['x','y']).values
                            lonmin = lon.reduce(np.min,dim=['x','y']).values
                            lonmax = lon.reduce(np.max,dim=['x','y']).values
                            # Define a regular grid with 1D lat/lon arrays
                            target_lat = np.linspace(latmin, latmax, lat.sizes['y'])
                            target_lon = np.linspace(lonmin, lonmax, lon.sizes['x'])
                            # Create a target grid dataset
                            target_grid = xr.Dataset({
                                'latitude': (['latitude'], target_lat),
                                'longitude': (['longitude'], target_lon)
                            })
                            # Example: regrid only data variables that depend on lat/lon
                            data_vars = [v for v in ds.data_vars if {'x', 'y'} <= set(ds[v].dims)]
                            # Loop and regrid each variable
                            ds_regridded = xr.Dataset()
                            for var2 in data_vars:
                                if 'time' in var2:
                                    continue
                                regridder = xe.Regridder(ds[var2], target_grid, method='bilinear',
                                                         ignore_degenerate=True)
                                ds_regridded[var2] = regridder(ds[var2])
                            ds_regridded = ds_regridded.assign_coords(time=ds.time)

                            # # Create a regridder object to go from curvilinear to regular grid
                            # regridder = xe.Regridder(ds, target_grid, method='bilinear',ignore_degenerate=True)
                            # # Regrid the entire dataset
                            # ds_regridded = regridder(ds)
                            # Add units to latitude and longitude coordinates
                            ds_regridded['latitude'].attrs['units'] = 'degrees_north'
                            ds_regridded['longitude'].attrs['units'] = 'degrees_east'
                            # Convert all float32 variables in the dataset to float64
                            ds_regridded = ds_regridded.astype('float64')
                            ds_regridded['time'] = ds_regridded['time'].astype('datetime64[ns]')
                            try:
                                self.interpolator[world_attrs.variable_alias[var]] = pyinterp.backends.xarray.Grid4D(ds_regridded[var], geodetic=True)
                            except KeyError:
                                logger.warning(f"key {var} not found in world attributes variable aliases")
                                continue
                            if self.cache:
                                self.export_interp(key=world_attrs["variable_alias"][var],source_type=source_type,mission=mission)
                        elif source_type == SourceType.CMEMS:
                            world = xr.open_zarr(store=worlds.stores[key])
                            self.interpolator[world_attrs.variable_alias[var]] = pyinterp.backends.xarray.Grid4D(world[var],geodetic=True)
                            if self.cache:
                                self.export_interp(key=world_attrs["variable_alias"][var],source_type=source_type,mission=mission)
                        elif source_type == SourceType.LOCAL:
                            ds = xr.open_dataset(worlds.stores[key])
                            # rename time and depth dimensions to be consistent
                            ds = ds.rename({"deptht": "depth", "time_counter": "time"})
                            lat = ds['nav_lat']
                            lon = ds['nav_lon']
                            # Define a regular grid with 1D lat/lon arrays
                            # reduce arrays to get max and min values
                            latmin = lat.reduce(np.min,dim=['x','y']).values
                            latmax = lat.reduce(np.max,dim=['x','y']).values
                            lonmin = lon.reduce(np.min,dim=['x','y']).values
                            lonmax = lon.reduce(np.max,dim=['x','y']).values
                            # Define a regular grid with 1D lat/lon arrays
                            target_lat = np.linspace(latmin, latmax, lat.sizes['y'])
                            target_lon = np.linspace(lonmin, lonmax, lon.sizes['x'])
                            # Create a target grid dataset
                            target_grid = xr.Dataset({
                                 'latitude': (['latitude'], target_lat),
                                 'longitude': (['longitude'], target_lon)
                             })
                            # Create a regridder object to go from curvilinear to regular grid
                            regridder = xe.Regridder(ds, target_grid, method='bilinear',ignore_degenerate=True)
                            # Regrid the entire dataset
                            ds_regridded = regridder(ds)
                            # Add units to latitude and longitude coordinates
                            ds_regridded['latitude'].attrs['units'] = 'degrees_north'
                            ds_regridded['longitude'].attrs['units'] = 'degrees_east'
                            # Convert all float32 variables in the dataset to float64
                            ds_regridded = ds_regridded.astype('float64')
                            ds_regridded['time'] = ds_regridded['time'].astype('datetime64[ns]')
                            self.interpolator[world_attrs.variable_alias[var]] = pyinterp.backends.xarray.Grid4D(ds_regridded[var],geodetic=True)
                            if self.cache:
                                self.export_interp(key=world_attrs["variable_alias"][var],source_type=source_type,mission=mission)
                        else:
                            logger.error(f"unknown model source {source_type.name}")
                            raise UnknownSourceKey

                        logger.info(f"built {var} from source {source_type.name} into interpolator: {world_attrs.variable_alias[var]}")
        logger.info("interpolators built successfully")

    def import_interp(self,key:str,source_type:SourceType,mission:str):
        if not os.path.isdir(f"interpolator_cache/{mission}"):
            return False
        import_loc = f"interpolator_cache/{mission}/{source_type.value}_{key}.lerp"
        if os.path.exists(import_loc):
            with open(import_loc, 'rb') as f:
                compressed_pickle = f.read()
            depressed_pickle = blosc.decompress(compressed_pickle)
            self.interpolator[key] = pickle.loads(depressed_pickle)
            logger.info(f"imported interpolator for {key} from source {source_type.name} for {mission}")
            return True
        else:
            logger.info(f"interpolator {key} not found for source {source_type.name} for {mission}")
            return False

    def export_interp(self,key:str,source_type:SourceType,mission:str):
        if not os.path.isdir(f"interpolator_cache/{mission}"):
            os.mkdir(f"interpolator_cache")
            os.mkdir(f"interpolator_cache/{mission}")
        pickled_data = pickle.dumps(self.interpolator[key])
        compressed_pickle = blosc.compress(pickled_data)
        with open(f"interpolator_cache/{mission}/{source_type.value}_{key}.lerp", 'wb') as f:
            f.write(compressed_pickle)
        logger.info(f"exported interpolator {key} for source {source_type.name} for {mission}")
