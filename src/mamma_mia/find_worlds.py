import os
from mamma_mia.catalog import Cats
from loguru import logger
import numpy as np
from attrs import frozen, field
from mamma_mia.inventory import inventory
import xarray as xr
from mamma_mia.worlds import WorldExtent, MatchedWorld, WorldType, FieldTypeWithRank, DomainType, SourceType,SourceConfig


@frozen
class FindWorlds:
    """
    Worlds class: contains a dictionary of matched worlds and the methods used to find them
    """
    entries: dict[str,MatchedWorld] = field(factory=dict)

    def search_worlds(self, cat:Cats, payload:dict[str,np.ndarray],extent,source:SourceConfig):
        for key in payload.keys():
            match source.source_type:
                case SourceType.CMEMS:
                    self.__find_cmems_worlds(cat=cat, key=key, extent=extent)
                case SourceType.LOCAL:
                    if SourceConfig.local_dir is None:
                        SourceConfig.local_dir = os.getcwd()
                        logger.info(f"using local directory {SourceConfig.local_dir}")
                    self.__find_local_worlds(extent=extent,key=key,local_dir=source.local_dir)
                case _:
                    raise ValueError(f"unknown source type {source.source_type.name}")


    def __find_local_worlds(self,key:str, extent:WorldExtent, local_dir:str) -> None:
        # if there are any alternative sources built a list of their source names.
        alternative_sources = inventory.parameters.entries[key].alternate_sources
        alternative_source_names = {}
        for src in alternative_sources:
            alternative_source_names[src] = inventory.parameters.entries[src].source_names
        for dirpath, _, filenames in os.walk(local_dir):
            for filename in filenames:
                if filename.endswith('.nc'):
                    nc_path = os.path.join(dirpath, filename)
                    ds = xr.open_dataset(nc_path)
                    for key2, var in ds.data_vars.items():
                        if key2 in inventory.parameters.entries[key].source_names:
                            ## if the variable is not in source names (quite likely) then need to search the alternative source names created above
                            alternative_parameter = None
                            for alt_key, alt_src in alternative_source_names.items():
                                if key2 in alt_src:
                                    alternative_parameter = alt_key
                                    break
                            if self.__check_subset(ds=ds,extent=extent):
                                logger.success(f"found a match in {filename} for parameter {key}")
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
        for k1, v1 in cat.cmems_cat.items():
            logger.info(f"searching cmems {k1}")
            for i in range(len(v1)):
                # ensure it is a numerical model
                if v1[i]["sources"][0] != "Numerical models":
                    # logger.warning(f"{v1[i]['sources'][0]} is not a numerical model")
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
                        if key not in inventory.parameters.entries.keys():
                            #logger.warning(f"variable {key} not in alias file")
                            continue
                        ## if the variable is not in source names (quite likely) then need to search the alternative source names created above
                        alternative_parameter = None
                        for alt_key,alt_src in alternative_source_names.items():
                            if variables[m]["short_name"] in alt_src:
                                alternative_parameter = alt_key
                                break
                        # check to see if variable matches source names or alterative parameter
                        if variables[m]["short_name"] in inventory.parameters.entries[key].source_names or alternative_parameter is not None:
                            # TODO add in a NAN check here in case extent has nans rather than values
                            # if trajectory spatial extent is within variable data
                            if (variables[m]["bbox"][0] < extent.lon_min and
                                    variables[m]["bbox"][1] < extent.lat_min
                                    and variables[m]["bbox"][2] > extent.lon_max and
                                    variables[m]["bbox"][3] > extent.lat_max):
                                depth_len = 0
                                # get length of depth dimension
                                for coord in variables[m]['coordinates']:
                                    if coord["coordinates_id"] == "depth":
                                        depth_len = coord["values"].__len__()
                                # if depth dimension is single value i.e. 2D then skip dataset
                                if depth_len == 1:
                                    continue
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
                                    #step = variables[m]["coordinates"][n]["values"][1] - \
                                    #       variables[m]["coordinates"][n]["values"][0]
                                except TypeError:
                                    start = variables[m]["coordinates"][n]["minimum_value"]
                                    end = variables[m]["coordinates"][n]["maximum_value"]
                                    #step = variables[m]["coordinates"][n]["step"]
                                # convert trajectory datetimes into timestamps to be able to compare with CMEMS catalog
                                start_traj = float((np.datetime64(extent.time_start) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                end_traj = float((np.datetime64(extent.time_end) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                # check if trajectory temporal extent is within variable data
                                if start_traj > start and end_traj < end:
                                    parts = dataset["dataset_id"].split("_")
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
                                    # after all that PHEW! we can add to matched entries
                                    logger.success(f"found a match in {dataset['dataset_id']} for {key}")
                                    # TODO validation on remaining fields if appropriate, e.g. do we need to validate resolution?

                                    new_world = MatchedWorld(
                                        data_id = dataset["dataset_id"],
                                        world_type=WorldType.from_string(enum_string=parts[1]),
                                        domain=domain_type,
                                        dataset_name=parts[3],
                                        resolution=parts[5],
                                        field_type=field_type,
                                        variable_alias={variables[m]["short_name"]:key},
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
                                                if variables[m]["short_name"] not in self.entries[world_id].variable_alias.keys():
                                                    self.entries[world_id].variable_alias[key5] = var5
                                            for key6,var6 in existing_alts.items():
                                                if variables[m]["short_name"] not in self.entries[world_id].alternative_parameter.keys():
                                                    self.entries[world_id].alternative_parameter[key6] = var6
                                        else:
                                            # if ranking is not better than just update with the variable name
                                            logger.info(f"updating {dataset['dataset_id']} with key {key} for field type {field_type.field_type.name}")
                                            if variables[m]["short_name"] not in self.entries[world_id].variable_alias.keys():
                                                self.entries[world_id].variable_alias[variables[m]["short_name"]] = key
                                            if variables[m]["short_name"] not in self.entries[world_id].alternative_parameter.keys():
                                                self.entries[world_id].alternative_parameter[key] = alternative_parameter
                                    else:
                                        # world doesn't exist yet so just add as a complete entry
                                        logger.info(f"creating new matched world {dataset['dataset_id']} for key {key}")
                                        self.entries[world_id] = new_world




#
# def __find_msm_worlds(key :str ,cat :Cats ,matched_worlds :dict,extent:dict) -> dict:
#     """
#     function to find models/worlds within the msm source catalog for a given auv extent and sensor specification
#     Args:
#         key: string that represents the variable to find
#         cat: Cats object that contains the catalogs
#         matched_worlds: dictionary of matched worlds that is updated with matched models that are found for each key
#         extent: dictionary containing spatial and temporal extents of the auv
#
#     Returns:
#         matched worlds dictionary containing dataset ids and variable names
#
#     """
#     for k1 ,v1 in cat.msm_cat.items():
#         var_key = None
#         logger.info(f"searching {k1}")
#         metadata = v1.describe()['metadata']
#         aliases = metadata.get('aliases', [])
#         # check if the key is in one of the variables alias dictionaries
#         for k2 ,v2 in aliases.items():
#             if key in v2:
#                 var_key = k2
#         spatial_extent = metadata.get('spatial_extent', [])
#         temporal_extent = metadata.get('temporal_extent', [])
#         start_traj = float((np.datetime64(extent["start_time"]) - np.datetime64(
#             '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
#         end_traj = float((np.datetime64(extent["end_time"]) - np.datetime64(
#             '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
#         if temporal_extent:
#             start_datetime = datetime.fromisoformat(temporal_extent[0].replace("Z", "+00:00")).timestamp( ) *1000
#             end_datetime = datetime.fromisoformat(temporal_extent[1].replace("Z", "+00:00")).timestamp( ) *1000
#             # Check if the item is within the desired date range and spatial bounds
#             if (spatial_extent and
#                     extent["min_lat"] >= spatial_extent[0] and extent["max_lat"] <= spatial_extent[2] and
#                     extent["min_lng"] >= spatial_extent[1] and extent["max_lng"] <= spatial_extent[3] and
#                     start_traj >= start_datetime and end_traj <= end_datetime and var_key is not None):
#                 logger.success(f"found a match in {k1} for {key}")
#                 if k1 in matched_worlds:
#                     logger.info(f"updating {k1} with key {key}")
#                     matched_worlds[k1][key] = var_key
#                 else:
#                     logger.info(f"creating new matched world {k1} for key {key}")
#                     matched_worlds[k1] = {key: var_key}
#     return matched_worlds

