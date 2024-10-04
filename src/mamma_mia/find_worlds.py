from mamma_mia.catalog import Cats,cmems_alias
from loguru import logger
from datetime import datetime
import numpy as np
import zarr

def find_worlds(cat: Cats,reality:zarr.Group,extent:dict) -> dict:
    """
    Function to search the catalog and return a dictionary of matched worlds/datasets for all catalog sources
    Args:
        cat: Cats object that contains the catalogs
        reality: reality zarr group containing initialised reality arrays
        extent: dictionary containing spatial and temporal extents

    Returns:
        dict: dictionary of matched worlds that can be used as a reference to download data subsets/worlds
    """
    # for every array in the reality group
    matched_worlds = {}
    # TODO see if a different approach can be used rather than using the reality keys e.g. use AUV sensor array attribute
    for key in reality.array_keys():
        logger.info(f"searching worlds for key {key}")
        matched_worlds = __find_cmems_worlds(key=key, cat=cat, matched_worlds=matched_worlds,extent=extent)
        matched_worlds = __find_msm_worlds(key=key, cat=cat, matched_worlds=matched_worlds,extent=extent)

    logger.success("world search completed successfully")
    return  matched_worlds

def __find_msm_worlds(key :str ,cat :Cats ,matched_worlds :dict,extent:dict) -> dict:
    """
    function to find models/worlds within the msm source catalog for a given auv extent and sensor specification
    Args:
        key: string that represents the variable to find
        cat: Cats object that contains the catalogs
        matched_worlds: dictionary of matched worlds that is updated with matched models that are found for each key
        extent: dictionary containing spatial and temporal extents of the auv

    Returns:
        matched worlds dictionary containing dataset ids and variable names

    """
    for k1 ,v1 in cat.msm_cat.items():
        var_key = None
        logger.info(f"searching {k1}")
        metadata = v1.describe()['metadata']
        aliases = metadata.get('aliases', [])
        # check if the key is in one of the variables alias dictionaries
        for k2 ,v2 in aliases.items():
            if key in v2:
                var_key = k2
        spatial_extent = metadata.get('spatial_extent', [])
        temporal_extent = metadata.get('temporal_extent', [])
        start_traj = float((np.datetime64(extent["start_time"]) - np.datetime64(
            '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
        end_traj = float((np.datetime64(extent["end_time"]) - np.datetime64(
            '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
        if temporal_extent:
            start_datetime = datetime.fromisoformat(temporal_extent[0].replace("Z", "+00:00")).timestamp( ) *1000
            end_datetime = datetime.fromisoformat(temporal_extent[1].replace("Z", "+00:00")).timestamp( ) *1000
            # Check if the item is within the desired date range and spatial bounds
            if (spatial_extent and
                    extent["min_lat"] >= spatial_extent[0] and extent["max_lat"] <= spatial_extent[2] and
                    extent["min_lng"] >= spatial_extent[1] and extent["max_lng"] <= spatial_extent[3] and
                    start_traj >= start_datetime and end_traj <= end_datetime and var_key is not None):
                logger.success(f"found a match in {k1} for {key}")
                if k1 in matched_worlds:
                    logger.info(f"updating {k1} with key {key}")
                    matched_worlds[k1][key] = var_key
                else:
                    logger.info(f"creating new matched world {k1} for key {key}")
                    matched_worlds[k1] = {key: var_key}
    return matched_worlds

def __find_cmems_worlds(key: str ,cat :Cats ,matched_worlds :dict,extent:dict) -> dict:
    """
    Traverses CMEMS catalog and find products/datasets that match the glider sensors and
    the trajectory spatial and temporal extent.

    Args:
        key: string that represents the variable to find
        cat: Cats object that contains the catalogs
        matched_worlds: dictionary of matched worlds that is updated with matched models that are found for each key

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
                        print(f"variable {key} not in alias file")
                    if variables[m]["short_name"] in cmems_alias[key]:
                        # if trajectory spatial extent is within variable data
                        if (variables[m]["bbox"][0] < extent["min_lng"] or
                                variables[m]["bbox"][1] > extent["min_lat"]
                                or variables[m]["bbox"][2] > extent["max_lng"] or
                                variables[m]["bbox"][3] > extent["min_lat"]):
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
                            start_traj = float((np.datetime64(extent["start_time"]) - np.datetime64(
                                '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                            end_traj = float((np.datetime64(extent["end_time"]) - np.datetime64(
                                '1970-01-01T00:00:00Z')) / np.timedelta64(1, 'ms'))
                            # check if trajectory temporal extent is within variable data
                            if start_traj > start and end_traj < end:
                                # make sure data is at least daily
                                if step <= 86400000:
                                    logger.success(f"found a match in {dataset['dataset_id']} for {key}")
                                    # TODO add support for multiple model types e.g. daily instantaneous, hourly mean etc
                                    mod_type = dataset['dataset_id'].split("_")[-1]
                                    if mod_type != "P1D-m":
                                        logger.warning("Only Daily means are currently supported in CMEMS sources")
                                        logger.info(f"{dataset['dataset_id']} will not be added as a matched world")
                                        continue
                                    if dataset["dataset_id"] in matched_worlds:
                                        logger.info(f"updating {dataset['dataset_id']} with key {key}")
                                        matched_worlds[dataset["dataset_id"]][key] = variables[m]["short_name"]
                                    else:
                                        logger.info(f"creating new matched world {dataset['dataset_id']} for key {key}")
                                        matched_worlds[dataset["dataset_id"]] = {key: variables[m]["short_name"]}
    return matched_worlds