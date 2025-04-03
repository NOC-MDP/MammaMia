from attrs import frozen,field,define
import zarr
from loguru import logger
import numpy as np
import sys
from mamma_mia.sensors import sensor_inventory
from mamma_mia.catalog import Cats
from mamma_mia.find_worlds import find_worlds
from mamma_mia.get_worlds import get_worlds
from mamma_mia.interpolator import Interpolators
from mamma_mia.exceptions import ValidationFailure, NullDataException
from mamma_mia.log import log_filter

@frozen
class Extent:
    """
    Immutable extent object, used to subset a model data source and download only what is needed for velocity interpolation

    Args:
        max_lat: maximum latitude required
        min_lat: minimum latitude required
        max_lng: maximum longitude required
        min_lng: minimum longitude required
        max_depth: maximum depth required
        start_dt: start datetime in format "2023-01-01T00:00:00Z"
        end_dt: end datetime in format "2023-01-01T00:00:00Z"

    """
    max_lat: float
    min_lat: float
    max_lng: float
    min_lng: float
    max_depth: float
    start_datetime: np.datetime64 = field(init=False)
    end_datetime: np.datetime64 = field(init=False)
    start_dt: str
    end_dt: str

    def __attrs_post_init__(self):
        object.__setattr__(self, 'start_datetime', np.datetime64(self.start_dt))
        object.__setattr__(self, 'end_datetime', np.datetime64(self.end_dt))
        self._validate()

    def _validate(self):
        if self.max_lat > 90 or self.max_lat < -90:
            raise ValidationFailure(f"Maximum Latitude {self.max_lat} failed validation")
        if self.min_lat > 90 or self.min_lat < -90:
            raise ValidationFailure(f"Minimum Latitude {self.min_lat} failed validation")
        if self.max_lng > 180 or self.max_lng < -180:
            raise ValidationFailure(f"Maximum Longitude {self.max_lng} failed validation")
        if self.min_lng > 180 or self.min_lng < -180:
            raise ValidationFailure(f"Minimum Longitude {self.min_lng} failed validation")


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
    temperature: float
    salinity: float

@define
class RealityWorld(zarr.Group):
    """
    An velocity world zarr group, based on a mamma mia world class that contains a subset of velocity data ready for interpolation onto points

    Args:
        extent: Extent object
        store: Zarr store to store object in, default: memory store
        overwrite: if store exists overwrite, default: False
        excess_space: increase in spatial extent of subset over extent provided, default 0.5 degrees
        excess_depth: increase in depth of subset over extent provided, default 100 meters
        msm_priority: priority value of MSM sources (higher has more priority) default = 2
        cmems_priority: priority value of CMEMS sources (higher has more priority) default = 1

    """
    extent: Extent
    store = None
    overwrite = False
    excess_space: float = 0.5
    excess_depth: int = 100
    msm_priority: int = 2
    cmems_priority: int = 1

    def __attrs_post_init__(self):
        logger.info("creating velocity world")
        # Create the group using the separate method
        group = zarr.group(store=self.store, overwrite=self.overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        self.attrs["name"] = "reality_world"
        self.attrs["description"] = "world to get interpolated reality"

        traj = self.create_group("trajectory")
        traj.array(name="latitudes",data=np.array(-999.999))
        traj.array(name="longitudes",data=np.array(-999.999))
        traj.array(name="depths",data=np.array(-999.999))
        traj.array(name="datetimes",data=np.array(np.datetime64('1970-01-01'),dtype='datetime64'))

        worlds = self.create_group("world")
        extent_excess = {
            "max_lat": self.extent.max_lat + self.excess_space,
            "min_lat": self.extent.min_lat - self.excess_space,
            "max_lng": self.extent.max_lng + self.excess_space,
            "min_lng": self.extent.min_lng - self.excess_space,
            # TODO dynamically set the +/- delta on start and end time based on time step of model (need at least two time steps)
            "start_time": np.datetime_as_string(self.extent.start_datetime - np.timedelta64(30, 'D'), unit="D"),
            "end_time": np.datetime_as_string(self.extent.end_datetime + np.timedelta64(30, 'D'), unit="D"),
            "max_depth": self.extent.max_depth + self.excess_depth
        }
        worlds.attrs["extent"] = extent_excess
        worlds.attrs["catalog_priorities"] = {"msm": self.msm_priority, "cmems": self.cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}

        real_grp = self.create_group("reality")
        # create cats
        cats = Cats()
        ctd = sensor_inventory.create_entity(entity_name="ctd", sensor_type="CTD", sensor_ref="mamma_mia")
        adcp = sensor_inventory.create_entity(entity_name="adcp", sensor_type="ADCP", sensor_ref="mamma_mia")

        for name,sensor in adcp.parameters.items():
            real_grp.empty(name=name,shape=1,dtype=np.float64)
        for name,sensor in ctd.parameters.items():
            real_grp.empty(name=name,shape=1,dtype=np.float64)

        matched_worlds = find_worlds(cat=cats,extent=extent_excess,reality=self.reality)
        self.world.attrs.update({"matched_worlds": matched_worlds})
        zarr_stores = get_worlds(cat=cats, world=self.world)
        self.world.attrs.update({"zarr_stores": zarr_stores})
        logger.success("reality world created successfully")

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
        for key in self.reality.array_keys():
            try:
                self.reality[key] = interpolator.interpolator[key].quadrivariate(location)
            except KeyError:
                pass
                #logger.warning(f"no interpolator for {key}")

        if np.isnan(self.reality["WATERCURRENTS_U"][0]):
            if point.depth >= 0.5:
                logger.error(f"U component velocity is NaN, depth {point.depth} is non zero and locatino is lat: {point.latitude} lng: {point.longitude}")
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

        if np.isnan(self.reality["WATERCURRENTS_W"][0]):
            if point.depth >= 0.5:
                logger.error(f"W component velocity is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
                raise NullDataException
            w_velocity = 0.0
        else:
            w_velocity = self.reality["WATERCURRENTS_W"][0]

        if np.isnan(self.reality["TEMP"][0]):
            if point.depth >= 0.5:
                logger.error(f"temperature is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
                raise NullDataException
            temperature = 15.00
        else:
            temperature = self.reality["TEMP"][0]

        if np.isnan(self.reality["CNDC"][0]):
            if point.depth >= 0.5:
                logger.error(f"salinity is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}")
                raise NullDataException
            salinity = 34.5
        else:
            salinity = self.reality["CNDC"][0]

        reality = RealityPt(u_velocity=u_velocity,
                            v_velocity=v_velocity,
                            w_velocity=w_velocity,
                            salinity=salinity,
                            temperature=temperature
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
    extent: Extent
    world: RealityWorld = field(init=False)
    interpolators: Interpolators = field(init=False)
    verbose: bool = False

    def __attrs_post_init__(self):
        # reset logger
        logger.remove()        # set logger based on requested verbosity
        if self.verbose:
            logger.add(sys.stdout, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="INFO")
        else:
            logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=log_filter)
        logger.info("creating velocity reality")
        self.world = RealityWorld(extent=self.extent)
        self.interpolators = Interpolators()
        self.interpolators.build(worlds=self.world["world"],mission="DVR")
        logger.success("reality created successfully")

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
