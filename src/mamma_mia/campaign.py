import json

from mamma_mia.catalog import Cats
from mamma_mia.mission import Mission
from mamma_mia.interpolator import Interpolators
from mamma_mia.auv import AUV,Slocum,ALR1500
from mamma_mia.sensors import CTD,BIO,ADCP
from mamma_mia.exceptions import AUVExists,UnknownAUV,UnknownSensor,MissionExists
from dataclasses import dataclass,field,asdict
import uuid
from loguru import logger
import zarr
from os import sep
import sys


@dataclass
class Campaign:
    """
    Campaign object, this contains all the missions that auv's are being deployed to undertake. It is the main object
    to interact with Mamma mia.

    Args:
        name: name of the campaign
        description: description of the campaign

    Returns:
        Campaign object with initialised catalog and system generated uuid

    """
    name: str
    description: str
    catalog: Cats = field(init=False, default_factory=Cats)
    auvs: dict[str,AUV] = field(default_factory=dict)
    missions: dict[str, Mission] = field(init=False, default_factory=dict)
    interpolators: dict[str, Interpolators] = field(init=False,default_factory=dict)
    uuid: uuid = uuid.uuid4()
    verbose: bool = False

    def __post_init__(self):
        # reset logger
        logger.remove()        # set logger based on requested verbosity
        if self.verbose:
            logger.add(sys.stdout, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="INFO")
        else:
            logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="WARNING")
        self.catalog = Cats()
        logger.success(f"Campaign {self.name} created")

    def add_auv(self,
                id:str,
                type:Slocum | ALR1500,
                sensor_arrays:list[CTD | BIO | ADCP]):
        """
        Add an auv to the campaign AUV dictionary
        Args:
            id: auv reference id, it is used as a key in the campaign dictionary
            type: auv type
            sensor_arrays: sensor arrays to attach to auv

        Returns:
            auv object stored in the campaign auv dictionary under its id key

        """
        logger.info(f"adding auv {id} to campaign {self.name}")
        if id in self.auvs:
            logger.error(f"Auv {id} already exists in {self.name}")
            raise AUVExists
        self.auvs[id] = AUV(type=type,id=id)
        self.auvs[id].add_sensor_arrays(sensor_arrays=sensor_arrays)
        logger.success(f"Auv {id} added to {self.name}")
    def add_mission(self,
                    name:str,
                    description:str,
                    auv:str,
                    trajectory_path:str,
                    store=None,
                    overwrite=False,
                    excess_space: int = 0.5,
                    excess_depth: int = 100,
                    msm_priority: int = 2,
                    cmems_priority: int = 1,
                    ) -> ():
        """
        Function that adds an auv mission to the campaign.
        Args:
            name: name of the mission
            description: description of the mission
            auv: AUV object that has been created with an specified sensor array
            trajectory_path: path to auv trajectory netcdf
            store: specify zarr store (Directory etc) default is memory store
            overwrite: overwrite an existing mission store, default is false
            excess_space: amount of excess space to add to model/world download in decimal degrees, default is 0.5
            excess_depth: amount of excess depth to add to model/world download in metres, default is 100
            msm_priority: priority value for msm world sources (higher values have greater priority)
            cmems_priority: priority value for cmems world sources (higher values have greater priority)

        Returns:
            Campaign object with initialised mission object contained within the missions dictionary. An interpolators object
            is also initialized and stored in the interpolated dictionary coded with the mission key. (each mission has its own
            set of interpolators).
        """
        if name in self.missions:
            logger.error(f"mission {name} already exists")
            raise MissionExists
        mission = Mission(name=name,
                          description=description,
                          auv=self.auvs[auv],
                          trajectory_path=trajectory_path,
                          store=store,
                          overwrite=overwrite,
                          excess_space=excess_space,
                          excess_depth=excess_depth,
                          msm_priority=msm_priority,
                          cmems_priority=cmems_priority
                          )
        interpolator = Interpolators()
        logger.info(f"adding {mission.attrs['name']} to {self.name}")
        logger.info(f"adding {auv} to {mission.attrs['name']}")
        self.missions[mission.attrs['name']] = mission
        self.interpolators[mission.attrs['name']] = interpolator
        logger.success(f"successfully added {mission.attrs['name']} to {self.name}")

    def build_missions(self) -> ():
        """
        Function that builds the missions contained within the missions dictionary.

        Returns:
            void: mission objects with searched and downloaded worlds and built interpolators ready for flight/deployments

        """
        logger.info(f"building {self.name} missions")
        for mission in self.missions.values():
            logger.info(f"building {mission.attrs['name']}")
            mission.build_mission(cat=self.catalog)
            logger.success(f"successfully built {mission.attrs['name']}")
        for key, interpol in self.interpolators.items():
            logger.info(f"building interpolator for mission {key}")
            interpol.build(worlds=self.missions[key]["world"])
            logger.success(f"successfully built interpolator for {key}")

    def run(self) -> ():
        """
        Function that runs the missions contained within the missions dictionary.
        Returns:
            void: populated reality data arrays in each mission within the missions dictionary. This emulates each auv
                  mission deployment.

        """
        logger.info(f"running {self.name}")
        for mission in self.missions.values():
            logger.info(f"flying {mission.attrs['name']}")
            mission.fly(self.interpolators[mission.attrs['name']])
        logger.success(f"{self.name} finished successfully")

    def export(self,overwrite=True,export_path=None) -> ():
        """
        Function that exports the campaign object as an zarr group
        Args:
            overwrite: overwrite any existing campaign store
            export_path: override default location of campaign store export.

        Returns:
            void: Campaign object is exported to zarr store. NOTE: interpolators and catalogs cannot be exported.

        """
        logger.info(f"exporting {self.name}")
        if export_path is None:
            logger.info(f"creating zarr store at {self.name}.zarr")
            export_path = f"{self.name}.zarr"
        else:
            logger.info(f"exporting zarr store at {export_path}{sep}{self.name}.zarr")
        store = zarr.DirectoryStore(f"{export_path}")
        logger.info(f"creating zarr group {self.name} in store")
        camp = zarr.group(store=store,overwrite=overwrite)
        camp.attrs['name'] = self.name
        camp.attrs['description'] = self.description
        camp.attrs['uuid'] = str(self.uuid)
        logger.success(f"zarr group {self.name} successfully created")
        dim_map = None
        for key1, mission in self.missions.items():
            # TODO need to dynamically build this rather than hardcoding it.
            # TODO do this by using mission[key].keys()
            print(list[mission.reality.keys()])
            print(list[mission.trajectory.keys()])
            print(list[mission.world.keys()])
            dim_map = {
                f"{mission.attrs['name']}/reality/nitrate": ['time'],
                f"{mission.attrs['name']}/reality/phosphate": ['time'],
                f"{mission.attrs['name']}/reality/pressure": ['time'],
                f"{mission.attrs['name']}/reality/salinity": ['time'],
                f"{mission.attrs['name']}/reality/silicate": ['time'],
                f"{mission.attrs['name']}/reality/temperature": ['time'],
                f"{mission.attrs['name']}/trajectory/datetimes": ['time'],
                f"{mission.attrs['name']}/trajectory/depths": ['time'],
                f"{mission.attrs['name']}/trajectory/latitudes": ['time'],
                f"{mission.attrs['name']}/trajectory/longitudes": ['time'],
                f"{mission.attrs['name']}/world/cmems_mod_glo_bgc_my_0.25deg_P1D-m/no3": ['time', 'depth','latitude','longitude'],
                f"{mission.attrs['name']}/world/cmems_mod_glo_bgc_my_0.25deg_P1D-m/po4": ['time', 'depth', 'latitude', 'longitude'],
                f"{mission.attrs['name']}/world/cmems_mod_glo_bgc_my_0.25deg_P1D-m/si": ['time', 'depth', 'latitude', 'longitude'],
                f"{mission.attrs['name']}/world/cmems_mod_glo_phy_my_0.083deg_P1D-m/so": ['time', 'depth', 'latitude', 'longitude'],
                f"{mission.attrs['name']}/world/cmems_mod_glo_phy_my_0.083deg_P1D-m/thetao": ['time', 'depth', 'latitude', 'longitude'],
                f"{mission.attrs['name']}/world/msm_eORCA12/so": ['time_counter','deptht','latitude','longitude'],
                f"{mission.attrs['name']}/world/msm_eORCA12/thetao": ['time_counter', 'deptht', 'latitude', 'longitude'],
            }
        for mission in self.missions.values():
            logger.info(f"creating zarr group for mission {mission.attrs['name']}")
            camp.create_group(mission.attrs['name'])
            logger.info(f"exporting {mission.attrs['name']}")
            zarr.copy_all(source=mission,dest=camp[mission.attrs['name']])
            if dim_map is None:
                raise Exception("dimension mapping attribute has not been generated")
            self.add_array_dimensions(group=camp,dim_map=dim_map)
            logger.success(f"successfully exported {mission.attrs['name']}")
        logger.info(f"consolidating metadata for {export_path}")
        zarr.consolidate_metadata(export_path)
        logger.success(f"successfully exported {self.name}")


    def add_array_dimensions(self,group, dim_map, path=""):
        """
        Recursively add _ARRAY_DIMENSIONS attribute to all arrays in a Zarr group, including nested groups.

        Parameters:
        group (zarr.Group): The root Zarr group to start with.
        dim_map (dict): A dictionary mapping array paths to their corresponding dimension names.
        path (str): The current path in the group hierarchy (used to track nested groups).
        """
        for name, item in group.items():
            # Construct the full path by appending the current item name
            full_path = f"{path}/{name}" if path else name

            # If the item is a group, recurse into it
            if isinstance(item, zarr.Group):
                self.add_array_dimensions(item, dim_map, full_path)
            # If the item is an array, add the _ARRAY_DIMENSIONS attribute
            elif isinstance(item, zarr.Array):
                if full_path in dim_map:
                    item.attrs["_ARRAY_DIMENSIONS"] = dim_map[full_path]
                    logger.info(f"Added _ARRAY_DIMENSIONS to {full_path}: {dim_map[full_path]}")
                else:
                    logger.warning(f"No dimension information found for {full_path}")