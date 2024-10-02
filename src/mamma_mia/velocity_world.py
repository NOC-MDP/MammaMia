from dataclasses import dataclass, fields, InitVar,field
import zarr
import uuid
from loguru import logger
import numpy as np
from mamma_mia.catalog import Cats
from mamma_mia.find_worlds import find_worlds
from mamma_mia.get_worlds import get_worlds
from mamma_mia.sensors import ADCP
from mamma_mia.interpolator import Interpolators


@dataclass(frozen=True)
class Extent:
    max_lat: float
    min_lat: float
    max_lng: float
    min_lng: float
    max_depth: float
    start_time: np.datetime64
    end_time: np.datetime64

@dataclass(frozen=True)
class Point:
    latitude: float
    longitude: float
    depth: float
    datetime: np.datetime64

@dataclass(frozen=True)
class Vector:
    u_velocity: float
    v_velocity: float
    w_velocity: float

@dataclass
class VelocityWorld(zarr.Group):

    def __init__(self,
                 extent: Extent,
                 store=None,
                 overwrite=False,
                 excess_space: float = 0.5,
                 excess_depth: int = 100,
                 msm_priority: int = 2,
                 cmems_priority: int = 1,

                 ):
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
            "start_time": np.datetime_as_string(extent.start_time - np.timedelta64(30, 'D'), unit="D"),
            "end_time": np.datetime_as_string(extent.end_time + np.timedelta64(30, 'D'), unit="D"),
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
                real_grp.full(name=sensor.default.type, shape=1, dtype=np.float64, fill_value=np.nan)
                real_grp.attrs["mapped_name"] = sensor.default.type

        matched_worlds = find_worlds(cat=cats,extent=extent_excess,reality=self["reality"])
        self.world.attrs.update({"matched_worlds": matched_worlds})
        zarr_stores = get_worlds(cat=cats, world=self.world)
        self.world.attrs.update({"zarr_stores": zarr_stores})

    def get_vector(self,point:Point,interpolator:Interpolators) -> Vector:
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
                logger.warning(f"no interpolator for {key}")

        vector = Vector(u_velocity=self.reality["u_component"][0],
                        v_velocity=self.reality["v_component"][0],
                        w_velocity=self.reality["w_component"][0],)
        return vector

@dataclass
class Velocity:
    extent: InitVar[Extent]
    velocity_world: VelocityWorld = field(init=False)
    interpolators: Interpolators = field(init=False)

    def __post_init__(self, extent:Extent):
        self.velocity_world = VelocityWorld(extent=extent)
        self.interpolators = Interpolators()
        self.interpolators.build(worlds=self.velocity_world["world"])

    def vector(self, point: Point) -> Vector:
        return self.velocity_world.get_vector(point=point, interpolator=self.interpolators)
