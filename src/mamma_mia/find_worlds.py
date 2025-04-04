from mamma_mia.catalog import Cats,cmems_alias,model_field_alias,field_rank_map
from mamma_mia.exceptions import UnknownModelField
from loguru import logger
import numpy as np
import zarr
from attrs import frozen, field


@frozen
class MatchedWorld:
    data_id: str
    source: str
    world_type: str
    domain: str
    dataset_name: str
    resolution: str
    field_type: str
    variable_alias: dict

    def __attrs_post_init__(self):
        # TODO add some validation here
        pass

@frozen
class Worlds:
    entries: dict[str,MatchedWorld] = field(factory=dict)

    def search_worlds(self, cat:Cats, payload:zarr.Group,extent:dict):
        for key in payload.array_keys():
            self.__find_cmems_worlds(cat=cat,key=key,extent=extent)

    def __find_cmems_worlds(self,key: str ,cat :Cats,extent:dict) -> None:
        """
        Traverses CMEMS catalog and find products/datasets that match the glider sensors and
        the trajectory spatial and temporal extent.

        Args:
            key: string that represents the variable to find
            cat: Cats object that contains the catalogs

        Returns:
            matched worlds dictionary containing dataset ids and variable names that reside within it.
        """
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
                        if key not in cmems_alias:
                            #logger.warning(f"variable {key} not in alias file")
                            continue
                        if variables[m]["short_name"] in cmems_alias[key]:
                            # if trajectory spatial extent is within variable data
                            if (variables[m]["bbox"][0] < extent["min_lng"] and
                                    variables[m]["bbox"][1] < extent["min_lat"]
                                    and variables[m]["bbox"][2] > extent["max_lng"] and
                                    variables[m]["bbox"][3] > extent["max_lat"]):
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
                                start_traj = float((np.datetime64(extent["start_time"]) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                end_traj = float((np.datetime64(extent["end_time"]) - np.datetime64(
                                    '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                                # check if trajectory temporal extent is within variable data
                                if start_traj > start and end_traj < end:
                                    parts = dataset["dataset_id"].split("_")
                                    # skip any interim datasets
                                    if "myint" in parts:
                                        continue

                                    field_type = parts[-1]
                                    # find the field type alias
                                    field_type_alias = None
                                    for k3, v3 in model_field_alias.items():
                                        if field_type in v3:
                                            field_type_alias = k3
                                            break
                                    if field_type_alias is None:
                                        raise UnknownModelField(f"field type {field_type} is not supported")
                                    world_id = "_".join(parts[:-1])
                                    logger.success(f"found a match in {dataset['dataset_id']} for {key}")
                                    new_world = MatchedWorld(
                                        data_id = dataset["dataset_id"],
                                        source=parts[0],
                                        world_type=parts[1],
                                        domain=parts[2],
                                        dataset_name=parts[3],
                                        resolution=parts[5],
                                        field_type=field_type_alias,
                                        variable_alias={variables[m]["short_name"]:key}
                                    )
                                    if world_id in self.entries:
                                        if field_rank_map[self.entries[world_id].field_type] > field_rank_map[new_world.field_type]:
                                            # get any existing variables
                                            existing_vars = self.entries[world_id].variable_alias
                                            self.entries[world_id] = new_world
                                            # add new variables if they aren't already present
                                            for key5,var5 in existing_vars.items():
                                                if variables[m]["short_name"] not in self.entries[world_id].variable_alias.keys():
                                                    self.entries[world_id].variable_alias[key5] = var5
                                        else:
                                            logger.info(f"updating {dataset['dataset_id']} with key {key} for field type {field_type_alias}")
                                            if variables[m]["short_name"] not in self.entries[world_id].variable_alias.keys():
                                                self.entries[world_id].variable_alias[variables[m]["short_name"]] = key
                                    else:
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

