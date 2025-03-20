
from mamma_mia.mission import Mission
from mamma_mia.interpolator import Interpolators
from mamma_mia import create_platform_class
from mamma_mia.exceptions import MissionExists, PlatformExists, UnknownPlatform
from loguru import logger
import zarr
from os import sep
import sys
from attrs import define, field
from mamma_mia.log import log_filter
from mamma_mia.catalog import Cats, cmems_alias

@define
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
    catalog: Cats = field(factory=Cats)
    platforms: dict[str,create_platform_class()] = field(factory=dict)
    missions: dict[str, Mission] = field(factory=dict)
    interpolators: dict[str, Interpolators] = field(factory=dict)
    verbose: bool = False

    def __attrs_post_init__(self):
        # reset logger
        logger.remove()        # set logger based on requested verbosity
        if self.verbose:
            logger.add(sys.stdout, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="INFO")
        else:
            logger.add(sys.stderr, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="DEBUG",filter=log_filter)
        logger.success(f"Campaign {self.name} created")

    def init_catalog(self):
        self.catalog = Cats()
        self.catalog.init_catalog()

    def register_platform(self,platform: create_platform_class(),name:str):
        """
        Add an platform to the campaign platform dictionary
        Args:
            platform: platform object to add to campaign
            name: name of the platform instance
        Returns:
            platform object stored in the campaign auv dictionary under its id key

        """
        if name in self.platforms:
            logger.error(f"{name} already exists in {self.name}")
            raise PlatformExists
        self.platforms[name] = platform
        logger.success(f"{name} successfully registered to {self.name}")

    def add_mission(self,
                    mission_name:str,
                    summary:str,
                    title:str,
                    platform_name:str,
                    trajectory_path:str,
                    store=None,
                    overwrite=False,
                    excess_space: int = 0.5,
                    extra_depth: int = 100,
                    msm_priority: int = 2,
                    cmems_priority: int = 1,
                    ) -> None:
        """
        Function that adds an auv mission to the campaign.
        Args:
            summary: sumary of mission
            platform_name:
            mission_name: name of the mission
            title: title of the mission
            trajectory_path: path to auv trajectory netcdf
            store: specify zarr store (Directory etc) default is memory store
            overwrite: overwrite an existing mission store, default is false
            excess_space: amount of excess space to add to model/world download in decimal degrees, default is 0.5
            extra_depth: amount of excess depth to add to model/world download in metres, default is 100
            msm_priority: priority value for msm world sources (higher values have greater priority)
            cmems_priority: priority value for cmems world sources (higher values have greater priority)

        Returns:
            Campaign object with initialised mission object contained within the missions dictionary. An interpolators object
            is also initialized and stored in the interpolated dictionary coded with the mission key. (each mission has its own
            set of interpolators).
        """
        if mission_name in self.missions:
            logger.error(f"mission {mission_name} already exists")
            raise MissionExists
        try:
            platform_n = self.platforms[platform_name]
        except KeyError:
            raise UnknownPlatform

        mission = Mission(mission=mission_name,
                          title=title,
                          summary=summary,
                          platform=platform_n,
                          trajectory_path=trajectory_path,
                          store=store,
                          overwrite=overwrite,
                          excess_space=excess_space,
                          extra_depth=extra_depth,
                          msm_priority=msm_priority,
                          cmems_priority=cmems_priority
                          )
        interpolator = Interpolators()
        self.missions[mission.attrs['mission']] = mission
        self.interpolators[mission.attrs['mission']] = interpolator
        logger.success(f"successfully added mission {mission.attrs['mission']} to campaign {self.name}")

    def build_missions(self) -> None:
        """
        Function that builds the missions contained within the missions dictionary.

        Returns:
            void: mission objects with searched and downloaded worlds and built interpolators ready for flight/deployments

        """
        logger.info(f"building {self.name} missions")
        for mission in self.missions.values():
            logger.info(f"building {mission.attrs['mission']}")
            mission.build_mission(cat=self.catalog)
            logger.success(f"successfully built {mission.attrs['mission']}")
        for key, interpol in self.interpolators.items():
            logger.info(f"building interpolators for {key}")
            interpol.build(worlds=self.missions[key]["world"],mission=key)
            logger.success(f"successfully built interpolators for {key}")

    def enable_interpolator_cache(self) -> None:
        """
        enable interpolator cache so generated intepolators are stored on disk

        """
        for key, interpol in self.interpolators.items():
            interpol.cache = True
            logger.info(f"enabled interpolator cache for {key}")

    def run(self) -> ():
        """
        Function that runs the missions contained within the missions dictionary.
        Returns:
            void: populated reality data arrays in each mission within the mission's dictionary. This emulates each auv
                  mission deployment.

        """
        logger.info(f"running {self.name}")
        for mission in self.missions.values():
            logger.info(f"flying {mission.attrs['mission']}")
            mission.fly(self.interpolators[mission.attrs['mission']])
        logger.success(f"{self.name} finished successfully")

    def export(self,overwrite=True,export_path=None) -> None:
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
        #camp.attrs['uuid'] = str(self.uuid)
        logger.success(f"zarr group {self.name} successfully created")

        for key1, mission in self.missions.items():
            mission.create_dim_map(cmems_alias=cmems_alias,msm_cat=self.catalog.msm_cat)
            logger.info(f"creating zarr group for mission {mission.attrs['mission']}")
            camp.create_group(mission.attrs['mission'])
            logger.info(f"exporting {mission.attrs['mission']}")
            zarr.copy_all(source=mission,dest=camp[mission.attrs['mission']])
            mission.add_array_dimensions(group=camp,dim_map= mission.world.attrs["dim_map"])
            logger.success(f"successfully exported {mission.attrs['mission']}")
        logger.info(f"consolidating metadata for {export_path}")
        zarr.consolidate_metadata(export_path)
        logger.success(f"successfully exported {self.name}")

