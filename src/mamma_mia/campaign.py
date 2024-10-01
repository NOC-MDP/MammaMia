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

    def add_auv(self,id:str,type:str,sensor_arrays:list):
        """
        Add an auv to the campaign AUV dictionary
        Args:
            id: auv reference id, it is used as a key in the campaign dictionary
            type: auv type
            sensor_arrays: sensor arrays to attach to auv

        Returns:
            auv object stored in the campaign auv dictionary under its id key

        """
        if id in self.auvs:
            logger.error(f"Auv {id} already exists in {self.name}")
            raise AUVExists
        if type == "slocum":
            type = Slocum()
        elif type == "alr1500":
            type = ALR1500()
        else:
            logger.error(f"unknown auv type {type}")
            raise UnknownAUV
        self.auvs[id] = AUV(type=type,id=id)
        array = []
        for sensor in sensor_arrays:
            if sensor == "CTD":
                array.append(CTD())
            elif sensor == "BIO":
                array.append(BIO())
            elif sensor == "ADCP":
                array.append(ADCP())
            else:
                logger.error(f"unknown sensor type {sensor}")
                raise UnknownSensor
        self.auvs[id].add_sensor_arrays(sensor_arrays=array)

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
        for mission in self.missions.values():
            logger.info(f"creating zarr group for mission {mission.attrs['name']}")
            camp.create_group(mission.attrs['name'])
            logger.info(f"exporting {mission.attrs['name']}")
            zarr.copy_all(source=mission,dest=camp[mission.attrs['name']])
            logger.success(f"successfully exported {mission.attrs['name']}")
        logger.success(f"successfully exported {self.name}")

    # TODO dynamically build this from the auv and sensor py files

    @staticmethod
    def list_auv_types() -> str :
        logger.info(f"listing available auvs")
        auvs = {
            "Slocum_Glider": asdict(Slocum()),
            "ALR1500": asdict(ALR1500()),
        }
        return json.dumps(auvs)

    @staticmethod
    def list_sensor_arrays()-> str:
        logger.info(f"listing available sensor arrays")
        arrays = {
            "CTD": asdict(CTD()),
            "BIO": asdict(BIO()),
            "ADCP": asdict(ADCP()),
        }
        return json.dumps(arrays)