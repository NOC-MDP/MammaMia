from dataclasses import dataclass,field
import zarr
import numpy as np
import xarray as xr
import pyinterp
import pyinterp.backends.xarray
from loguru import logger
import xesmf as xe

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
        interpolator_priorities = worlds.attrs["interpolator_priorities"]
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
                            ds = ds.rename({"deptht": "depth", "time_counter": "time"})
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
                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(ds_regridded[var], geodetic=True)
                            # create or update priorities of interpolator datasetsc
                            interpolator_priorities[k1] = worlds.attrs["catalog_priorities"]["msm"]
                        elif split_key[0] == "cmems":
                            if self.__check_priorities(key=k1, source="cmems",worlds=worlds):
                                continue
                            world = xr.open_zarr(store=worlds.attrs["zarr_stores"][key])
                            self.interpolator[k1] = pyinterp.backends.xarray.Grid4D(world[var],geodetic=True)
                            interpolator_priorities[k1] = worlds.attrs["catalog_priorities"]["cmems"]
                        else:
                            logger.error("unknown model source key")
                            raise Exception

                        logger.info(f"built {var} from source {split_key[0]} into interpolator: {k1}")
        worlds.attrs.update({"interpolator_priorities": interpolator_priorities})
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