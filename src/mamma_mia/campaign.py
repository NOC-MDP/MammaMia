from mamma_mia.catalog import Cats
from mamma_mia.mission import Mission
from mamma_mia.interpolator import Interpolators
from mamma_mia.auv import AUV
from dataclasses import dataclass,field
import uuid
from loguru import logger
import zarr
from os import sep

@dataclass
class Campaign:
    name: str
    description: str
    catalog: Cats = field(init=False, default_factory=Cats)
    missions: dict[str, Mission] = field(init=False, default_factory=dict)
    interpolators: dict[str, Interpolators] = field(init=False,default_factory=dict)
    uuid: uuid = uuid.uuid4()

    def __post_init__(self):
        self.catalog = Cats()
        logger.success(f"Campaign {self.name} created")

    def add_mission(self,
                    name:str,
                    description:str,
                    auv:AUV,
                    trajectory_path:str,
                    store=None,
                    overwrite=False,
                    excess_space: int = 0.5,
                    excess_depth: int = 100,
                    msm_priority: int = 2,
                    cmems_priority: int = 1,
                    ) -> ():
        mission = Mission(name=name,
                          description=description,
                          auv=auv,
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
        logger.info(f"running {self.name}")
        for mission in self.missions.values():
            logger.info(f"flying {mission.attrs['name']}")
            mission.fly(self.interpolators[mission.attrs['name']])
        logger.success(f"{self.name} finished successfully")

    def export(self,overwrite=True,export_path=None) -> ():
        logger.info(f"exporting {self.name}")
        if export_path is None:
            logger.info(f"creating zarr store at {self.name}.zarr")
            export_path = f"{self.name}.zarr"
        else:
            logger.info(f"exporting zarr store at {export_path}{sep}{self.name}.zarr")
        store = zarr.DirectoryStore(f"{export_path}{sep}{self.name}.zarr")
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