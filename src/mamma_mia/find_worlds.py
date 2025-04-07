from mamma_mia.catalog import Cats,cmems_alias
from loguru import logger
import numpy as np
import zarr
from attrs import frozen, field
from enum import Enum

class WorldType(Enum):
    model = "mod"
    observation = "obs"
    @classmethod
    def from_string(cls,enum_string:str) -> "WorldType":
        match enum_string:
            case "mod":
                logger.info("setting world type to model")
                return WorldType.model
            case "obs":
                logger.info("setting world type to observation")
                return WorldType.observation
            case _:
                raise ValueError(f"unknown world type {enum_string}")

class SourceType(Enum):
    cmems = "cmems"
    msm = "msm"
    @classmethod
    def from_string(cls,enum_string:str) -> "SourceType":
        match enum_string:
            case "cmems":
                logger.info("setting source type to cmems")
                return SourceType.cmems
            case "msm":
                logger.info("setting source type to msm")
                return SourceType.msm
            case _:
                raise ValueError(f"unknown source type {enum_string}")


class FieldType(Enum):
    six_hour_instant = "PT6H-i"
    daily_mean = "P1D-m"
    monthly_mean = "P1M-m"
    @classmethod
    def from_string(cls,enum_string:str) -> "FieldType":
        match enum_string:
            case "PT6H-i":
                return FieldType.six_hour_instant
            case "P1D-m":
                return FieldType.daily_mean
            case "P1M-m":
                return FieldType.monthly_mean
            case _:
                raise ValueError(f"unknown field type {enum_string}")

@frozen
class FieldTypeWithRank:
    field_type: FieldType
    rank: int
    @classmethod
    def from_string(cls,enum_string:str, rank:int=None) -> "FieldTypeWithRank":
        match enum_string:
            case "PT6H-i":
                if rank is None:
                    rank = 1
                return cls(field_type=FieldType.six_hour_instant, rank=rank)
            case "P1D-m":
                if rank is None:
                    rank = 2
                return cls(field_type=FieldType.daily_mean, rank=rank)
            case "P1M-m":
                if rank is None:
                    rank = 3
                return cls(field_type=FieldType.monthly_mean, rank=rank)
            case _:
                raise ValueError(f"unknown field type {enum_string}")

# TODO figure out why only domains that work are global
class DomainType(Enum):
    globe = "glo"
    #arctic = "arc"
    @classmethod
    def from_string(cls,enum_string:str) -> "DomainType":
        match enum_string:
            case "glo":
                logger.info("setting domain type to glo")
                return DomainType.globe
            case _:
                raise ValueError(f"unknown domain type {enum_string}")

@frozen
class MatchedWorld:
    data_id: str
    source: SourceType
    world_type: WorldType
    domain: DomainType
    dataset_name: str
    resolution: str
    field_type: FieldTypeWithRank
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

                                    try:
                                        field_type = FieldTypeWithRank.from_string(enum_string=parts[-1])
                                    except ValueError:
                                        logger.warning(f"{parts[-1]} is not a supported field type")
                                        continue
                                    world_id = "_".join(parts[:-1])
                                    try:
                                        domain_type = DomainType.from_string(enum_string=parts[2])
                                    except ValueError:
                                        logger.warning(f"domain {parts[2]} not supported, skipping this dataset")
                                        continue
                                    logger.success(f"found a match in {dataset['dataset_id']} for {key}")
                                    # TODO validation to ensure that the parts of the parsed string are valid fields.
                                    new_world = MatchedWorld(
                                        data_id = dataset["dataset_id"],
                                        source=SourceType.from_string(enum_string=parts[0]),
                                        world_type=WorldType.from_string(enum_string=parts[1]),
                                        domain=domain_type,
                                        dataset_name=parts[3],
                                        resolution=parts[5],
                                        field_type=field_type,
                                        variable_alias={variables[m]["short_name"]:key}
                                    )
                                    if world_id in self.entries:
                                        if self.entries[world_id].field_type.rank > new_world.field_type.rank:
                                            # get any existing variables
                                            existing_vars = self.entries[world_id].variable_alias
                                            self.entries[world_id] = new_world
                                            # add new variables if they aren't already present
                                            for key5,var5 in existing_vars.items():
                                                if variables[m]["short_name"] not in self.entries[world_id].variable_alias.keys():
                                                    self.entries[world_id].variable_alias[key5] = var5
                                        else:
                                            logger.info(f"updating {dataset['dataset_id']} with key {key} for field type {field_type.field_type.name}")
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

