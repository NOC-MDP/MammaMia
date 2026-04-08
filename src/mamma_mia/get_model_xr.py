import os

import copernicusmarine
import xarray as xr
from loguru import logger
from OceanDataStore import OceanDataCatalog


def get_worlds(model_id: str, mission: xr.DataTree) -> xr.DataTree:
    parts = model_id.split("-")
    parts2 = model_id.split("_")
    store = ""
    if parts[0] == "noc":
        store = __get_NOC_worlds(model_id=model_id, mission=mission)
    if parts2[0] == "cmems":
        store = __get_cmems_worlds(model_id=model_id, mission=mission)

    mission.assign_attrs(store=store)
    return mission


def __get_cmems_worlds(model_id: str, mission) -> str:
    """
    function that downloads model data from CMEMS, data must match the temporal and spatial extents of the auv, and also
    have the required variables to match the sensor arrays of the auv.
    Args:
        value: object that contains the intake entry of the matched dataset
        worlds:

    Returns:
        string that represents the zarr store location of the downloaded data. The world zarr group is also updated with
        the downloaded model data.

    """

    zarr_f = (
        f"{model_id}_{mission.attrs['geospatial_attrs']['geospatial_lon_max']}_{mission.attrs['geospatial_attrs']['geospatial_lon_min']}_"
        f"{mission.attrs['geospatial_attrs']['geospatial_lat_max']}_{mission.attrs['geospatial_attrs']['geospatial_lat_min']}_"
        f"{mission.attrs['geospatial_attrs']['geospatial_vertical_max']}_{mission.attrs['geospatial_attrs']['time_coverage_start']}_"
        f"{mission.attrs['geospatial_attrs']['time_coverage_end']}.zarr"
    )
    zarr_d = "copernicus-data/"
    logger.info(f"getting cmems model {zarr_f}")
    if not os.path.isdir(zarr_d + zarr_f):
        logger.info(f"{zarr_f} has not been cached, downloading now")
        copernicusmarine.subset(
            dataset_id=model_id,
            variables=list(mission["platform"].attrs["sensors"]),
            minimum_longitude=float(
                mission.attrs["geospatial_attrs"]["geospatial_lon_min"]
            ),
            maximum_longitude=float(
                mission.attrs["geospatial_attrs"]["geospatial_lon_max"]
            ),
            minimum_latitude=float(
                mission.attrs["geospatial_attrs"]["geospatial_lat_min"]
            ),
            maximum_latitude=float(
                mission.attrs["geospatial_attrs"]["geospatial_lat_max"]
            ),
            start_datetime=str(
                mission.attrs["geospatial_attrs"]["time_coverage_start"]
            ),
            end_datetime=str(mission.attrs["geospatial_attrs"]["time_coverage_end"]),
            minimum_depth=0,
            maximum_depth=float(
                mission.attrs["geospatial_attrs"]["geospatial_vertical_max"]
            ),
            output_filename=zarr_f,
            output_directory=zarr_d,
            file_format="zarr",
        )
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f


def __get_NOC_worlds(model_id: str, mission) -> str:
    """
    Function that downloads the NOC source model data that matches the required spatial and temporal extents and sensor
    specification of the auv.
    Args:
        key: model source
        worlds:

    Returns:
        string that represents the zarr store location of the downloaded data. The world zarr group is also updated with
        the downloaded model data.
    """
    catalog = OceanDataCatalog(catalog_name="noc-model-stac")
    zarr_f = (
        f"{model_id}_{mission.attrs['geospatial_attrs']['geosptial_lon_max']}_{mission.attrs['geospatial_attrs']['geosptial_lon_min']}_"
        f"{mission.attrs['geospatial_attrs']['geosptial_lat_max']}_{mission.attrs['geospatial_attrs']['geosptial_lat_min']}_"
        f"{mission.attrs['geospatial_attrs']['geospatial_vertical_max']}_{mission.attrs['geospatial_attrs']['time_coverage_start']}_"
        f"{mission.attrs['geospatial_attrs']['time_coverage_end']}.zarr"
    )
    zarr_d = "NOC-data/"
    logger.info(f"getting NOC world {zarr_f}")
    if not os.path.isdir(zarr_d + zarr_f):
        logger.info(f"{zarr_f} has not been cached, downloading now")
        ds = catalog.open_dataset(
            id=model_id,
            start_datetime=mission.attrs["geospatial_attrs"]["time_coverage_start"],
            end_datetime=mission.attrs["geospatial_attrs"]["time_coverage_end"],
            bbox=(
                mission.attrs["geospatial_attrs"]["geosptial_lon_min"],
                mission.attrs["geospatial_attrs"]["geosptial_lat_min"],
                mission.attrs["geospatial_attrs"]["geosptial_lon_max"],
                mission.attrs["geospatial_attrs"]["geosptial_lat_max"],
            ),
        )
        ds.drop_encoding().to_zarr(store=zarr_d + zarr_f)
        logger.success(f"{zarr_f} has been cached")
    return zarr_d + zarr_f
