
from attrs import frozen,field,define
from loguru import logger
import numpy as np
import sys
from mamma_mia.mission import Trajectory
from mamma_mia.sensors import SensorInventory
from mamma_mia.catalog import Cats
from mamma_mia.get_worlds import get_worlds
from mamma_mia.interpolator import Interpolators
from mamma_mia.exceptions import NullDataException
from mamma_mia.log import log_filter
from mamma_mia.find_worlds import SourceType, SourceConfig, FindWorlds
from mamma_mia.worlds import WorldsAttributes,WorldsConf,WorldExtent


@frozen
class Point:
    """
    Immutable point object
    """
    latitude: float
    longitude: float
    depth: float
    datetime: np.datetime64 = field(init=False)
    dt: str

    def __attrs_post_init__(self):
        object.__setattr__(self, 'datetime', np.datetime64(self.dt))

@frozen
class RealityPt:
    """
    Immutable vector object, contains U, V and W components of velocity, temperature, salinity at a single point
    """
    u_velocity: float
    v_velocity: float
    w_velocity: float
    potential_temperature: float
    practical_salinity: float

@define
class RealityWorld:
    """
    An velocity world zarr group, based on a mamma mia world class that contains a subset of velocity data ready for interpolation onto points

    Args:


    """
    world_conf: WorldsConf
    trajectory: Trajectory
    reality: dict
    source: SourceConfig

    @classmethod
    def for_glidersim(cls,  extent:WorldExtent,
                            excess_depth:int=100,
                            excess_space:float=0.5,
                            msm_priority:int=2,
                            cmems_priority:int=1,
                      ):
        logger.info("creating reality world")

        trajectory = Trajectory.for_glidersim()

        extent_excess = WorldExtent(
            lat_max=np.float64(extent.lat_max + excess_space),
            lat_min=np.float64(extent.lat_min - excess_space),
            lon_max=np.float64(extent.lon_max + excess_space),
            lon_min=np.float64(extent.lon_min - excess_space),
            time_start=np.datetime_as_string(np.datetime64(extent.time_start) - np.timedelta64(30,'D'),unit="D"),
            time_end = np.datetime_as_string(np.datetime64(extent.time_end) + np.timedelta64(30,'D'),unit="D"),
            depth_max=np.float64(extent.depth_max + excess_depth)
        )

        attrs = WorldsAttributes(extent=extent_excess,
                                 catalog_priorities={"msm": msm_priority, "cmems": cmems_priority},
                                 interpolator_priorities={},
                                 matched_worlds={})

        worlds_conf = WorldsConf(attributes=attrs,worlds={},stores={})

        # create cats
        cats = Cats()
        cats.init_catalog()
        sensor_inventory = SensorInventory()
        ctd = sensor_inventory.create_entity(entity_name="ctd", sensor_ref="mm_ctd")
        adcp = sensor_inventory.create_entity(entity_name="adcp", sensor_ref="mm_adcp")

        reality = {}
        for name,sensor in adcp.parameters.items():
            reality[name] = np.empty(shape=1,dtype=np.float64)
        for name,sensor in ctd.parameters.items():
            reality[name] = np.empty(shape=1,dtype=np.float64)

        matched_worlds = FindWorlds()
        source = SourceConfig(source_type=SourceType.from_string("CMEMS"))
        matched_worlds.search_worlds(cat=cats,extent=extent_excess,payload=reality,source=source)
        worlds_conf.attributes.matched_worlds = matched_worlds.entries
        zarr_stores = get_worlds(cat=cats, worlds=worlds_conf,source=source)
        worlds_conf.stores = zarr_stores
        logger.success("reality world created successfully")

        return cls(trajectory=trajectory,
                    reality=reality,
                    world_conf=worlds_conf,
                    source=source,)

    def get_reality(self,point:Point,interpolator:Interpolators) -> RealityPt:
        """
        Interpolates a point object using the interpolators and returns a vector object containing the interpolated data

        Args:
            point: Point object
            interpolator: Interpolators object

        Returns:
            Vector object containing the interpolated velocity components

        """
        location = {
            "longitude": np.array([point.longitude],dtype=np.float64),
            "latitude": np.array([point.latitude],dtype=np.float64),
            "depth": np.array([point.depth],dtype=np.float64),
            "time": np.array([point.datetime], dtype='datetime64'),
        }
        for key in self.reality.keys():
            try:
                self.reality[key] = interpolator.interpolator[key].quadrivariate(location)
            except KeyError:
                pass
                #logger.warning(f"no interpolator for {key}")

        if np.isnan(self.reality["WATERCURRENTS_U"][0]):
            if point.depth >= 0.5:
                logger.error(f"U component velocity is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
                raise NullDataException
            u_velocity = 0.0
        else:
            u_velocity = self.reality["WATERCURRENTS_U"][0]

        if np.isnan(self.reality["WATERCURRENTS_V"][0]):
            if point.depth >= 0.5:
                logger.error(f"V component velocity is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
                raise NullDataException
            v_velocity = 0.0
        else:
            v_velocity = self.reality["WATERCURRENTS_V"][0]

        # if np.isnan(self.reality["WATERCURRENTS_W"][0]):
        #     if point.depth >= 0.5:
        #         logger.error(f"W component velocity is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
        #         raise NullDataException
        #     w_velocity = 0.0
        # else:
        #     w_velocity = self.reality["WATERCURRENTS_W"][0]

        if np.isnan(self.reality["CFSN0329"][0]):
            if point.depth >= 0.5:
                logger.error(f"temperature is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
                raise NullDataException
            potential_temperature = 15.00
        else:
            potential_temperature = self.reality["CFSN0329"][0]

        if np.isnan(self.reality["IADIHDIJ"][0]):
            if point.depth >= 0.5:
                logger.error(f"salinity is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
                raise NullDataException
            practical_salinity = 34.5
        else:
            practical_salinity = self.reality["IADIHDIJ"][0]

        reality = RealityPt(u_velocity=u_velocity,
                            v_velocity=v_velocity,
                            w_velocity=0.0,
                            practical_salinity=practical_salinity,
                            potential_temperature=potential_temperature
                            )
        return reality


@define
class Reality:
    """
    Velocity reality object, this contains the world, the interpolators and the extent required to generate interpolated
    velocity components

    Args:
        extent: Extent object

    """
    extent: WorldExtent
    world: RealityWorld
    interpolators: Interpolators
    verbose: bool = False

    @classmethod
    def for_glidersim(cls,extent: WorldExtent,verbose: bool = False):
        # reset logger
        logger.remove()        # set logger based on requested verbosity
        if verbose:
            logger.add(sys.stdout, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="INFO")
        else:
            logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=log_filter)
        logger.info("creating velocity reality")
        world = RealityWorld.for_glidersim(extent=extent)
        interpolators = Interpolators()
        interpolators.build(worlds=world.world_conf,mission="DVR",source_type=world.source.source_type)
        logger.success("reality created successfully")
        return cls(extent=extent,
                   world=world,
                   interpolators=interpolators,
                   verbose=verbose)

    def teleport(self, point: Point) -> RealityPt:
        """
        Teleports (interpolates) the point object using the generated interpolators and returns a vector object
        containing the interpolated velocity components

        Args:
            point: Point object

        Returns:
            Vector: Vector object
        """
        return self.world.get_reality(point=point, interpolator=self.interpolators)
