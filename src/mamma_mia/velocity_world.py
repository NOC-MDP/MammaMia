from dataclasses import dataclass, fields, InitVar,field
import zarr
import uuid
from loguru import logger
import numpy as np
from mamma_mia.catalog import Cats
from mamma_mia.find_worlds import find_worlds
from mamma_mia.get_worlds import get_worlds
from mamma_mia.sensors import ADCP, CTD
from mamma_mia.interpolator import Interpolators
from mamma_mia.exceptions import ValidationFailure, NullDataException


@dataclass(frozen=True)
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
    start_dt: InitVar[str]
    end_dt: InitVar[str]

    def __post_init__(self, start_dt:str, end_dt:str):
        object.__setattr__(self, 'start_datetime', np.datetime64(start_dt))
        object.__setattr__(self, 'end_datetime', np.datetime64(end_dt))
        self.validate()

    def validate(self):
        if self.max_lat > 90 or self.max_lat < -90:
            raise ValidationFailure(f"Maximum Latitude {self.max_lat} failed validation")
        if self.min_lat > 90 or self.min_lat < -90:
            raise ValidationFailure(f"Minimum Latitude {self.min_lat} failed validation")
        if self.max_lng > 180 or self.max_lng < -180:
            raise ValidationFailure(f"Maximum Longitude {self.max_lng} failed validation")
        if self.min_lng > 180 or self.min_lng < -180:
            raise ValidationFailure(f"Minimum Longitude {self.min_lng} failed validation")


@dataclass(frozen=True)
class Point:
    """
    Immutable point object
    """
    latitude: float
    longitude: float
    depth: float
    datetime: np.datetime64 = field(init=False)
    dt: InitVar[str]

    def __post_init__(self, dt:str):
        object.__setattr__(self, 'datetime', np.datetime64(dt))

@dataclass(frozen=True)
class Vector:
    """
    Immutable vector object, contains U, V and W components of velocity at a single point
    """
    u_velocity: float
    v_velocity: float
    w_velocity: float

@dataclass(frozen=True)
class Density:
    """
    Immutable density object, contains temperature and salinity for a single point
    """
    temperature: float
    salinity: float

@dataclass
class VelocityWorld(zarr.Group):
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
    def __init__(self,
                 extent: Extent,
                 store=None,
                 overwrite=False,
                 excess_space: float = 0.5,
                 excess_depth: int = 100,
                 msm_priority: int = 2,
                 cmems_priority: int = 1,

                 ):
        logger.info("creating velocity world")
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        self.attrs["name"] = "velocity_world"
        self.attrs["uuid"] = str(uuid.uuid4())
        self.attrs["description"] = "world to get interpolated velocities"

        traj = self.create_group("trajectory")
        traj.array(name="latitudes",data=np.array(-999.999))
        traj.array(name="longitudes",data=np.array(-999.999))
        traj.array(name="depths",data=np.array(-999.999))
        traj.array(name="datetimes",data=np.array(np.datetime64('1970-01-01'),dtype='datetime64'))

        worlds = self.create_group("world")
        extent_excess = {
            "max_lat": extent.max_lat + excess_space,
            "min_lat": extent.min_lat - excess_space,
            "max_lng": extent.max_lng + excess_space,
            "min_lng": extent.min_lng - excess_space,
            # TODO dynamically set the +/- delta on start and end time based on time step of model (need at least two time steps)
            "start_time": np.datetime_as_string(extent.start_datetime - np.timedelta64(30, 'D'), unit="D"),
            "end_time": np.datetime_as_string(extent.end_datetime + np.timedelta64(30, 'D'), unit="D"),
            "max_depth": extent.max_depth + excess_depth
        }
        worlds.attrs["extent"] = extent_excess
        worlds.attrs["catalog_priorities"] = {"msm": msm_priority, "cmems": cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}

        real_grp = self.create_group("reality")
        # create cats
        cats = Cats()
        adcp = ADCP()
        sensor_arrays = {"ADCP": {}}
        for sensor in fields(adcp):
            # filter out uuid field
            if "uuid" in sensor.name:
                sensor_arrays["ADCP"][sensor.name] = {"uuid": str(sensor.default)}
            # if field starts with sensor then it's a sensor!
            if "sensor" in sensor.name:
                # map sensor class to a JSON serializable object (a dict basically)
                sensor_arrays["ADCP"][sensor.name] = {"type":sensor.default.type,"units":sensor.default.units}
                # TODO look into why this is needed as it is only used for its keys should be able to use the sensor array above
                # TODO but find worlds is dependant on the reality group and it shouldn't be.
                real_grp.full(name=sensor.default.type, shape=1, dtype=np.float64, fill_value=np.nan)
                real_grp.attrs["mapped_name"] = sensor.default.type

        matched_worlds = find_worlds(cat=cats,extent=extent_excess,reality=self["reality"])
        self.world.attrs.update({"matched_worlds": matched_worlds})
        zarr_stores = get_worlds(cat=cats, world=self.world)
        self.world.attrs.update({"zarr_stores": zarr_stores})
        logger.success("velocity world created successfully")

    def get_vector(self,point:Point,interpolator:Interpolators) -> Vector:
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
                # TODO need to dynamically set up a list of components that should be there rather than assuming as sometimes W is not available
                if key != "w_component":
                    logger.warning(f"no interpolator for {key}")

        if np.isnan(self.reality["u_component"][0]):
            if point.depth >= 0.5:
                logger.warning(f"U component velocity is NaN, depth {point.depth} is non zero and locatino is lat: {point.latitude} lng: {point.longitude}, assuming zero velocity for this component")
            raise NullDataException
        else:
            u_velocity = self.reality["u_component"][0]

        if np.isnan(self.reality["v_component"][0]):
            if point.depth >= 0.5:
                logger.warning(f"V component velocity is NaN, depth {point.depth} is non zero and locatino is lat: {point.latitude} lng: {point.longitude}, assuming zero velocity for this component")
            raise NullDataException
        else:
            v_velocity = self.reality["v_component"][0]

        if np.isnan(self.reality["w_component"][0]):
            if point.depth >= 0.5:
                pass
                # logger.warning(f"W component velocity is NaN, depth {point.depth} is non zero and locatino is lat: {point.latitude} lng: {point.longitude}, assuming zero velocity for this component")
            raise NullDataException
        else:
            w_velocity = self.reality["w_component"][0]

        vector = Vector(u_velocity=u_velocity,
                        v_velocity=v_velocity,
                        w_velocity=w_velocity,)
        return vector

@dataclass
class DensityWorld(zarr.Group):
    """
    An density world zarr group, based on a mamma mia world class that contains a subset of temperature/salinity data ready for interpolation onto points

    Args:
        extent: Extent object
        store: Zarr store to store object in, default: memory store
        overwrite: if store exists overwrite, default: False
        excess_space: increase in spatial extent of subset over extent provided, default 0.5 degrees
        excess_depth: increase in depth of subset over extent provided, default 100 meters
        msm_priority: priority value of MSM sources (higher has more priority) default = 2
        cmems_priority: priority value of CMEMS sources (higher has more priority) default = 1

    """
    def __init__(self,
                 extent: Extent,
                 store=None,
                 overwrite=False,
                 excess_space: float = 0.5,
                 excess_depth: int = 100,
                 msm_priority: int = 2,
                 cmems_priority: int = 1,

                 ):
        logger.info("creating density world")
        # Create the group using the separate method
        group = zarr.group(store=store, overwrite=overwrite)

        # Initialize the base class with the created group attributes
        super().__init__(store=group.store, path=group.path, read_only=group.read_only, chunk_store=group.chunk_store,
                         synchronizer=group.synchronizer)

        self.attrs["name"] = "density_world"
        self.attrs["uuid"] = str(uuid.uuid4())
        self.attrs["description"] = "world to get interpolated temperature and salinity"

        traj = self.create_group("trajectory")
        traj.array(name="latitudes",data=np.array(-999.999))
        traj.array(name="longitudes",data=np.array(-999.999))
        traj.array(name="depths",data=np.array(-999.999))
        traj.array(name="datetimes",data=np.array(np.datetime64('1970-01-01'),dtype='datetime64'))

        worlds = self.create_group("world")
        extent_excess = {
            "max_lat": extent.max_lat + excess_space,
            "min_lat": extent.min_lat - excess_space,
            "max_lng": extent.max_lng + excess_space,
            "min_lng": extent.min_lng - excess_space,
            # TODO dynamically set the +/- delta on start and end time based on time step of model (need at least two time steps)
            "start_time": np.datetime_as_string(extent.start_datetime - np.timedelta64(30, 'D'), unit="D"),
            "end_time": np.datetime_as_string(extent.end_datetime + np.timedelta64(30, 'D'), unit="D"),
            "max_depth": extent.max_depth + excess_depth
        }
        worlds.attrs["extent"] = extent_excess
        worlds.attrs["catalog_priorities"] = {"msm": msm_priority, "cmems": cmems_priority}
        worlds.attrs["interpolator_priorities"] = {}
        worlds.attrs["matched_worlds"] = {}
        worlds.attrs["zarr_stores"] = {}

        real_grp = self.create_group("reality")
        # create cats
        cats = Cats()
        ctd = CTD()
        sensor_arrays = {"CTD": {}}
        for sensor in fields(ctd):
            # filter out uuid field
            if "uuid" in sensor.name:
                sensor_arrays["CTD"][sensor.name] = {"uuid": str(sensor.default)}
            # if field starts with sensor then it's a sensor!
            if "sensor" in sensor.name:
                # map sensor class to a JSON serializable object (a dict basically)
                sensor_arrays["CTD"][sensor.name] = {"type":sensor.default.type,"units":sensor.default.units}
                # TODO look into why this is needed as it is only used for its keys should be able to use the sensor array above
                # TODO but find worlds is dependant on the reality group and it shouldn't be.
                real_grp.full(name=sensor.default.type, shape=1, dtype=np.float64, fill_value=np.nan)
                real_grp.attrs["mapped_name"] = sensor.default.type

        matched_worlds = find_worlds(cat=cats,extent=extent_excess,reality=self["reality"])
        self.world.attrs.update({"matched_worlds": matched_worlds})
        zarr_stores = get_worlds(cat=cats, world=self.world)
        self.world.attrs.update({"zarr_stores": zarr_stores})
        logger.success("density world created successfully")

    def get_density(self,point:Point,interpolator:Interpolators) -> Density:
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
                # TODO need to dynamically set up a list of components that should be there rather than assuming as sometimes pressure is not available
                if key != "pressure":
                    logger.warning(f"no interpolator for {key}")

        if np.isnan(self.reality["temperature"][0]):
            if point.depth >= 0.5:
                logger.warning(f"temperature is NaN, depth {point.depth} is non zero and location is lat: {point.latitude} lng: {point.longitude}, assuming 14 degrees temperature")
            raise NullDataException
        else:
            temperature = self.reality["temperature"][0]

        if np.isnan(self.reality["salinity"][0]):
            if point.depth >= 0.5:
                logger.warning(f"salinity is NaN, depth {point.depth} is non zero and locatino is lat: {point.latitude} lng: {point.longitude}, assuming 35 PSU")
            raise NullDataException
        else:
            salinity = self.reality["salinity"][0]

        return Density(temperature=temperature,salinity=salinity)

@dataclass
class VelocityReality:
    """
    Velocity reality object, this contains the world, the interpolators and the extent required to generate interpolated
    velocity components

    Args:
        extent: Extent object

    """
    extent: InitVar[Extent]
    velocity_world: VelocityWorld = field(init=False)
    interpolators: Interpolators = field(init=False)

    def __post_init__(self, extent:Extent):
        logger.info("creating velocity reality")
        self.velocity_world = VelocityWorld(extent=extent)
        self.interpolators = Interpolators()
        self.interpolators.build(worlds=self.velocity_world["world"],mission="VR")
        logger.success("velocity reality created successfully")

    def teleport(self, point: Point) -> Vector:
        """
        Teleports (interpolates) the point object using the generated interpolators and returns a vector object
        containing the interpolated velocity components

        Args:
            point: Point object

        Returns:
            Vector: Vector object
        """
        return self.velocity_world.get_vector(point=point, interpolator=self.interpolators)

@dataclass
class DensityReality:
    """
    Velocity reality object, this contains the world, the interpolators and the extent required to generate interpolated
    velocity components

    Args:
        extent: Extent object

    """
    extent: InitVar[Extent]
    density_world: DensityWorld = field(init=False)
    interpolators: Interpolators = field(init=False)

    def __post_init__(self, extent:Extent):
        logger.info("creating density reality")
        self.density_world = DensityWorld(extent=extent)
        self.interpolators = Interpolators()
        self.interpolators.build(worlds=self.density_world["world"],mission="VR")
        logger.success("density reality created successfully")

    def teleport(self, point: Point) -> Density:
        """
        Teleports (interpolates) the point object using the generated interpolators and returns a vector object
        containing the interpolated velocity components

        Args:
            point: Point object

        Returns:
            Vector: Vector object
        """
        return self.density_world.get_density(point=point, interpolator=self.interpolators)
