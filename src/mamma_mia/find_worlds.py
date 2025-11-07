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
import copy
import os
from datetime import datetime

from mamma_mia.catalog import Cats
from loguru import logger
import numpy as np
from attrs import frozen, field
from mamma_mia.inventory import inventory
import xarray as xr
from mamma_mia.worlds import WorldExtent, MatchedWorld, WorldType, FieldTypeWithRank, DomainType, SourceType,SourceConfig, ResolutionTypeWithRank


@frozen
class FindWorlds:
    """
    Worlds class: contains a dictionary of matched worlds and the methods used to find them
    """
    entries: dict[str,MatchedWorld] = field(factory=dict)

    def search_worlds(self, cat:Cats, payload:dict[str,np.ndarray],extent,source:SourceConfig):
        """
        search world wrapper function, this runs the specific find world function for the specifed source configuration
        Args:
            cat:
            payload:
            extent:
            source:

        Returns:

        """
        for key in payload.keys():
            match source.source_type:
                case SourceType.CMEMS:
                    self.__find_cmems_worlds(cat=cat, key=key, extent=extent)
                case SourceType.LOCAL:
                    if SourceConfig.local_dir is None:
                        SourceConfig.local_dir = os.getcwd()
                        logger.info(f"using local directory {SourceConfig.local_dir}")
                    self.__find_local_worlds(extent=extent,key=key,local_dir=source.local_dir)
                case SourceType.MSM:
                    self.__find_msm_worlds(cat=cat, key=key, extent=extent)
                case _:
                    raise ValueError(f"unknown source type {source.source_type.name}")


    def __find_local_worlds(self,key:str, extent:WorldExtent, local_dir:str) -> None:
        """
        Searches a specified or if not specified the current working directory for netcdf files containing model source
        data that can be used as input.
        Args:
            key:
            extent:
            local_dir:

        Returns:

        """
        # if there are any alternative sources built a list of their source names.
        alternative_sources = inventory.parameters.entries[key].alternate_sources
        alternative_source_names = {}
        for src in alternative_sources:
            alternative_source_names[src] = inventory.parameters.entries[src].source_names
        for dirpath, _, filenames in os.walk(local_dir):
            for filename in filenames:
                # TODO ideally would handle more options such as zarr
                if filename.endswith('.nc'):
                    nc_path = os.path.join(dirpath, filename)
                    ds = xr.open_dataset(nc_path)
                    for key2, var in ds.data_vars.items():
                        alternative_parameter = None
                        for alt_key, alt_src in alternative_source_names.items():
                            if key2 in alt_src:
                                alternative_parameter = alt_key
                                break
                        try:
                            key_chk = key2 in inventory.parameters.entries[key].source_names or key2 in inventory.parameters.entries[alternative_parameter].source_names
                        except KeyError:
                            key_chk = key2 in inventory.parameters.entries[key].source_names
                        if key_chk:
                            if self.__check_subset(ds=ds,extent=extent):
                                field_type = self.__estimate_field_interval(ds=ds)
                                domain_type = self.__estimate_domain_type(ds=ds)
                                new_world = MatchedWorld(
                                    data_id=filename,
                                    world_type=WorldType.from_string(enum_string="mod"),
                                    domain=domain_type,
                                    dataset_name=filename,
                                    resolution="",
                                    field_type=field_type,
                                    variable_alias={key2: key},
                                    alternative_parameter={key: alternative_parameter},
                                    local_dir=local_dir,
                                )
                                # create a new world entry based on existing entries ranking and variables.
                                # NOTE this assumes that all variables of a dataset exist across all field types.
                                # TODO check that the assumption in the comment above is true
                                if filename in self.entries:
                                    # if the rank of existing world is higher (and therefore not as good) replace
                                    if self.entries[filename].field_type.rank > new_world.field_type.rank:
                                        # get any existing variables
                                        existing_vars = self.entries[filename].variable_alias
                                        # get any existing alternative variables
                                        existing_alts = self.entries[filename].alternative_parameter
                                        self.entries[filename] = new_world
                                        # add new variables if they aren't already present
                                        for key5, var5 in existing_vars.items():
                                            if key2 not in self.entries[
                                                filename].variable_alias.keys():
                                                self.entries[filename].variable_alias[key5] = var5
                                        for key6, var6 in existing_alts.items():
                                            if key2 not in self.entries[
                                                filename].alternative_parameter.keys():
                                                self.entries[filename].alternative_parameter[key6] = var6
                                    else:
                                        # if ranking is not better than just update with the variable name
                                        logger.info(
                                            f"updating {filename} with key {key} for field type {field_type.field_type.name}")
                                        if key2 not in self.entries[
                                            filename].variable_alias.keys():
                                            self.entries[filename].variable_alias[key2] = key
                                        if key2 not in self.entries[
                                            filename].alternative_parameter.keys():
                                            self.entries[filename].alternative_parameter[key] = alternative_parameter
                                else:
                                    # world doesn't exist yet so just add as a complete entry
                                    logger.info(f"creating new matched world {filename} for key {key}")
                                    self.entries[filename] = new_world

    @staticmethod
    def __check_subset(ds:xr.Dataset, extent:WorldExtent, fill_value:int = -1) -> bool:
        """
        Checks the input dataset to ensure the whole required extent fits within it
        Args:
            ds: xarray dataset
            extent: WorldExtent object
            fill_value: optional fill value to ignore

        Returns: True if subset is valid, False otherwise

        """
        lat = ds['nav_lat'].values
        lon = ds['nav_lon'].values

        # Mask out fill values (e.g., -1) before computing bounds
        valid_mask = (lat != fill_value) & (lon != fill_value)
        lat_valid = lat[valid_mask]
        lon_valid = lon[valid_mask]

        if lat_valid.size == 0 or lon_valid.size == 0:
            raise Exception("No valid lat/lon values in dataset.")

        # Get dataset bounds
        lat_min_ds = float(lat_valid.min())
        lat_max_ds = float(lat_valid.max())
        lon_min_ds = float(lon_valid.min())
        lon_max_ds = float(lon_valid.max())

        # Check if the full extent is covered
        if (
                lat_min_ds <= extent.lat_min and
                lat_max_ds >= extent.lat_max and
                lon_min_ds <= extent.lon_min and
                lon_max_ds >= extent.lon_max
        ):
            return True
        else:
            return False

    @staticmethod
    def __estimate_field_interval(ds:xr.Dataset) -> FieldTypeWithRank:
        """
        Estimates the field interval of the input data source, by checking the attributes of the first variable
        for a specific string that denotes its type

        Args:
            ds: xarray dataset

        Returns: FieldTypeWithRank of the relevent type

        """
        # TODO this only checks the first variable and only looks for a specific string so is really not that robust
        for key,value in ds.data_vars.items():
            for attrs in value.attrs.values():
                if "1 d" in attrs:
                    return FieldTypeWithRank.from_string(enum_string="P1D-m")
        raise Exception("Field interval check failed")


    @staticmethod
    def __estimate_domain_type(ds:xr.Dataset) -> DomainType:
        """
        estimates the domain of the input data source, options include global and regional
        The estimation is carried out by calculating the extent of the dataset and checking to see if it matches
        a global extent (absolute tolerance of 10 degrees).
        Args:
            ds: xarray dataset to check

        Returns: DomainType of the relevent type

        """
        # TODO search units of coords and looks for degrees_North to remove hard coding of lat and lon
        lat = ds["nav_lat"]
        lon = ds["nav_lon"]
        if np.isclose(float(np.abs(lat.max()-lat.min())),180.0,atol=10):
            if np.isclose(float(np.abs(lon.max()-lon.min())), 360.0, atol=10):
                return DomainType.from_string(enum_string="glo")
        else:
            return DomainType.from_string(enum_string="regional")

        raise Exception("Domain type check failed")

    def __find_cmems_worlds(self,key: str ,cat :Cats,extent) -> None:
        """
        Traverses CMEMS catalog and find products/datasets that match the glider sensors and
        the trajectory spatial and temporal extent.

        Args:
            key: string that represents the variable to find
            cat: Cats object that contains the catalogs

        Returns:
            matched worlds dictionary containing dataset ids and variable names that reside within it.
        """
        # if there are any alternative sources built a list of their source names.
        alternative_sources = inventory.parameters.entries[key].alternate_sources
        alternative_source_names = {}
        for src in alternative_sources:
            alternative_source_names[src] = inventory.parameters.entries[src].source_names
        for product in cat.cmems_cat.products:
            #check source is numerical model
            if "Numerical models" in product.sources:
                # check each dataset
                for dataset in product.datasets:
                    k = None
                    for k in range(len(dataset.versions[0].parts[0].services)):
                        if dataset.versions[0].parts[0].services[k].service_format == "zarr":
                            break
                    variables = dataset.versions[0].parts[0].services[k].variables
                    # check each variable
                    for m in range(len(variables)):
                        if key not in inventory.parameters.entries.keys():
                            #logger.warning(f"variable {key} not in alias file")
                            continue
                        ## if the variable is not in source names (quite likely) then need to search the alternative source names created above
                        alternative_parameter = None
                        for alt_key,alt_src in alternative_source_names.items():
                            if variables[m].short_name in alt_src:
                                alternative_parameter = alt_key
                                break
                        # check to see if variable matches source names or alterative parameter
                        if variables[m].short_name in inventory.parameters.entries[key].source_names or alternative_parameter is not None:
                            # TODO add in a NAN check here in case extent has nans rather than values
                            # if trajectory spatial extent is within variable data
                            if (variables[m].bbox[0] < extent.lon_min and
                                    variables[m].bbox[1] < extent.lat_min
                                    and variables[m].bbox[2] > extent.lon_max and
                                    variables[m].bbox[3] > extent.lat_max):
                                depth_len = 0
                                # get length of depth dimension
                                for coord in variables[m].coordinates:
                                    if coord.coordinate_id == "depth":
                                        # some multiple sources dataasets don't have any depth values so need to handle None
                                        try:
                                            depth_len = coord.values.__len__()
                                        except AttributeError:
                                            continue
                                # if depth dimension is single value i.e. 2D then skip dataset
                                if depth_len == 1:
                                    continue
                                # find the time coordinate index
                                n = None
                                for n in range(len(variables[m].coordinates)):
                                    if variables[m].coordinates[n].coordinate_id == "time":
                                        break
                                # get time values either as part of values list or as a specific max and min value
                                # both are possibilities it seems!
                                try:
                                    start = variables[m].coordinates[n].values[0]
                                    end = variables[m].coordinates[n].values[-1]
                                    #step = variables[m]["coordinates"][n]["values"][1] - \
                                    #       variables[m]["coordinates"][n]["values"][0]
                                except TypeError:
                                    start = variables[m].coordinates[n].minimum_value
                                    end = variables[m].coordinates[n].maximum_value
                                    #step = variables[m]["coordinates"][n]["step"]
                                # convert trajectory datetimes into timestamps to be able to compare with CMEMS catalog
                                start_traj = float((np.datetime64(extent.time_start) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                end_traj = float((np.datetime64(extent.time_end) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                # check if trajectory temporal extent is within variable data
                                if start_traj > start and end_traj < end:
                                    parts = dataset.dataset_id.split("_")
                                    # skip any interim datasets
                                    if "myint" in parts:
                                        continue
                                    # check to see if field type is supported by MM
                                    try:
                                        field_type = FieldTypeWithRank.from_string(enum_string=parts[-1])
                                    except ValueError:
                                        logger.warning(f"{parts[-1]} is not a supported field type")
                                        continue
                                    world_id = "_".join(parts[:-1])
                                    # check to see if domain type is supported by MM
                                    try:
                                        domain_type = DomainType.from_string(enum_string=parts[2])
                                    except ValueError:
                                        logger.warning(f"domain {parts[2]} not supported, skipping this dataset")
                                        continue
                                    # check is world type is supported
                                    try:
                                        world_type = WorldType.from_string(enum_string=parts[1])
                                    except ValueError:
                                        logger.warning(f"world type {parts[1]} not supported, skipping this dataset")
                                        continue
                                    # after all that PHEW! we can add to matched entries
                                    logger.success(f"found a match in {dataset.dataset_id} for {key}")
                                    # TODO validation on remaining fields if appropriate, e.g. do we need to validate resolution?
                                    new_world = MatchedWorld(
                                        data_id = dataset.dataset_id,
                                        world_type=world_type,
                                        domain=domain_type,
                                        dataset_name=parts[3],
                                        resolution=parts[5],
                                        field_type=field_type,
                                        variable_alias={variables[m].short_name:key},
                                        alternative_parameter={key:alternative_parameter}
                                    )
                                    # create a new world entry based on existing entries ranking and variables.
                                    # NOTE this assumes that all variables of a dataset exist across all field types.
                                    # TODO check that the assumption in the comment above is true
                                    if world_id in self.entries:
                                        # if the rank of existing world is higher (and therefore not as good) replace
                                        if self.entries[world_id].field_type.rank > new_world.field_type.rank:
                                            # get any existing variables
                                            existing_vars = self.entries[world_id].variable_alias
                                            # get any existing alternative variables
                                            existing_alts = self.entries[world_id].alternative_parameter
                                            self.entries[world_id] = new_world
                                            # add new variables if they aren't already present
                                            for key5,var5 in existing_vars.items():
                                                if variables[m].short_name not in self.entries[world_id].variable_alias.keys():
                                                    self.entries[world_id].variable_alias[key5] = var5
                                            for key6,var6 in existing_alts.items():
                                                if variables[m].short_name not in self.entries[world_id].alternative_parameter.keys():
                                                    self.entries[world_id].alternative_parameter[key6] = var6
                                        else:
                                            # if ranking is not better than just update with the variable name
                                            logger.info(f"updating {dataset.dataset_id} with key {key} for field type {field_type.field_type.name}")
                                            if variables[m].short_name not in self.entries[world_id].variable_alias.keys():
                                                self.entries[world_id].variable_alias[variables[m].short_name] = key
                                            if variables[m].short_name not in self.entries[world_id].alternative_parameter.keys():
                                                self.entries[world_id].alternative_parameter[key] = alternative_parameter
                                    else:
                                        # world doesn't exist yet so just add as a complete entry
                                        logger.info(f"creating new matched world {dataset.dataset_id} for key {key}")
                                        self.entries[world_id] = new_world

    def __find_msm_worlds(self,key :str ,cat :Cats,extent) -> None:
        """
        function to find models/worlds within the msm source catalog for a given auv extent and sensor specification
        Args:
            key: string that represents the variable to find
            cat: Cats object that contains the catalogs
            extent: dictionary containing spatial and temporal extents of the auv

        Returns:
            matched worlds dictionary containing dataset ids and variable names

        """
        # get source names for key from parameter inventory
        alternative_sources = inventory.parameters.entries[key].alternate_sources
        alternative_source_names = {}
        for src in alternative_sources:
            alternative_source_names[src] = inventory.parameters.entries[src].source_names
        # create datetimes from extent strings
        world_start = datetime.strptime(extent.time_start, "%Y-%m-%d")
        world_end = datetime.strptime(extent.time_end, "%Y-%m-%d")
        # for every item in msm catalog
        for item in cat.msm_cat.Items:
            # see if the item contains the required temporal and spatial extent
            if (
                    item.bbox[0] <= extent.lon_min and
                    item.bbox[2] >= extent.lon_max and
                    item.bbox[1] <= extent.lat_min and
                    item.bbox[3] >= extent.lat_max and
                    datetime.strptime(item.properties["start_datetime"], "%Y-%m-%dT%H:%M:%SZ") < world_start and
                    datetime.strptime(item.properties["end_datetime"], "%Y-%m-%dT%H:%M:%SZ") > world_end
            ):
                # check to see if item variable is in parameters list
                variables = item.properties["variables"]
                # check each variable
                for i in range(variables.__len__()):
                    alternative_parameter = None
                    for alt_key,alt_src in alternative_source_names.items():
                        if variables[i] in alt_src:
                            alternative_parameter = alt_key
                            break
                    if variables[i] in inventory.parameters.entries[key].source_names or alternative_parameter is not None:
                        parts = item.id.split("/")
                        # check to see if field type is supported by MM
                        try:
                            field_type = FieldTypeWithRank.from_string(enum_string=item.properties["operation_frequency"])
                        except ValueError:
                            logger.warning(f"{item.properties['operation_frequency']} is not a supported field type")
                            continue
                        world_id = item.id
                        # check to see if domain type is supported by MM
                        try:
                            if item.bbox == [-180.0, -90.0, 180.0, 90.0]:
                                domain_type = DomainType.from_string(enum_string="glo")
                            else:
                                domain_type = DomainType.from_string(enum_string="regional")
                        except ValueError as e:
                            logger.warning(f"domain {e} not supported, skipping this dataset")
                            continue
                        # check is world type is supported
                        try:
                            # TODO this should not be hardcoded, ideally need to locate a suitable field in catalog metadata
                            world_type = WorldType.from_string(enum_string="mod")
                        except ValueError as e:
                            logger.warning(f"world type {e} not supported, skipping this dataset")
                            continue
                        resolution_parts = parts[1].split("-")
                        try:
                            resolution = ResolutionTypeWithRank.from_string(enum_string=resolution_parts[1])
                        except ValueError as e:
                            logger.warning(f"resolution {e} not supported, skipping this dataset")
                            continue
                        # after all that PHEW! we can add to matched entries
                        logger.success(f"found a match in {item.id} for {key}")
                        new_world = MatchedWorld(
                            data_id=item.id,
                            world_type=world_type,
                            domain=domain_type,
                            dataset_name=parts[1],
                            resolution=resolution,
                            field_type=field_type,
                            variable_alias={item.properties["variables"][i]:key},
                            alternative_parameter={key:alternative_parameter}
                        )
                        # check existing worlds to see if the new one is better and replace if it is
                        for world_id2,world in self.entries.items():
                            if set(new_world.variable_alias) & set(world.variable_alias):
                                logger.info("found world with same variable alias, will assess which one to keep")
                                if new_world.field_type.rank < world.field_type.rank or new_world.resolution.rank < world.resolution.rank:
                                    logger.info("new model is ranked higher, replacing....")
                                    # update new world with any existing variable aliases and alternative parameters
                                    try:
                                        new_world.variable_alias.update(self.entries[world_id].variable_alias)
                                        new_world.alternative_parameter.update(self.entries[world_id].alternative_parameter)
                                    except KeyError as e:
                                        # this is raised if the world id doesn't already exist, i.e. if the model is better
                                        # rather than if another variable has already created the better model
                                        logger.debug(f"key {e} doesn't exist in world entries")
                                        pass
                                    del self.entries[world_id2]
                                    self.entries[world_id] = new_world
                                    logger.info(f"replaced world {world.data_id} with new world {new_world.data_id}")
                                    break

                        # check each world id to see if an entry needs updating for new variables etc.
                        if world_id in self.entries:
                            # if the rank of existing world is higher (and therefore not as good) replace
                            if self.entries[world_id].field_type.rank > new_world.field_type.rank:
                                # get any existing variables
                                existing_vars = self.entries[world_id].variable_alias
                                # get any existing alternative variables
                                existing_alts = self.entries[world_id].alternative_parameter
                                self.entries[world_id] = new_world
                                # add new variables if they aren't already present
                                for key5, var5 in existing_vars.items():
                                    if variables[i] not in self.entries[world_id].variable_alias.keys():
                                        self.entries[world_id].variable_alias[key5] = var5
                                for key6, var6 in existing_alts.items():
                                    if variables[i] not in self.entries[
                                        world_id].alternative_parameter.keys():
                                        self.entries[world_id].alternative_parameter[key6] = var6
                            else:
                                # if ranking is not better than just update with the variable name
                                logger.info(
                                    f"updating {item.id} with key {key} for field type {field_type.field_type.name}")
                                if variables[i] not in self.entries[world_id].variable_alias.keys():
                                    self.entries[world_id].variable_alias[variables[i]] = key
                                if variables[i] not in self.entries[world_id].alternative_parameter.keys():
                                    self.entries[world_id].alternative_parameter[key] = alternative_parameter
                        else:
                            # world doesn't exist yet so just add as a complete entry
                            logger.info(f"creating new matched world {item.id} for key {key}")
                            self.entries[world_id] = new_world


