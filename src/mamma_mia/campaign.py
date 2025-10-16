# Copyright 2025 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mamma_mia.mission import Mission, Creator, Contributor, Publisher
from mamma_mia.interpolator import Interpolators
from mamma_mia import create_platform_attrs
from mamma_mia.find_worlds import SourceType, SourceConfig
from mamma_mia.exceptions import MissionExists, PlatformExists, UnknownPlatform, InvalidEntity
from loguru import logger
import zarr
from os import sep
import sys
from attrs import define, field
from mamma_mia.log import log_filter
from mamma_mia.catalog import Cats

@define
class Campaign:
    """
    Campaign object, this contains all the missions that auv's are being deployed to undertake. It is the main object
    to interact with Mamma mia.

    Attributes
    ----------
    name : str, required
        Name of the Campaign.
    description : str, optional
        Description/Summary of the Campaign
    catalog : Cats
        The Mamma Mia catalog class
    platforms: dict[str, Platform]
        A dictionary containing platforms that can be used in missions
    missions: dict[str, Mission]
        A dictionary containing missions objects
    interpolators: dict[str, Interpolator]
        A dictionary containing interpolators, used to interpolate model data to a platforms trajectory
    verbose: bool
        Logging verbosity
    """
    name: str
    description: str
    catalog: Cats = Cats()
    platforms: dict[str,create_platform_attrs()] = field(factory=dict)
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


    def register_platform(self,entity: create_platform_attrs()):
        """
        Register a platform to the campaign platform dictionary

        Parameters
        -----------
        entity : PlatformAttributes
            Platform attributes object

        Raises
        -------
        InvalidEntity
            Platform name must not be None
        PlatformExists
            Platform name must not already be registered
        """
        if entity.entity_name is None:
            raise InvalidEntity("Platform entity name cannot be None")
        if entity.entity_name in self.platforms:
            logger.error(f"{entity.entity_name} already exists in {self.name}")
            raise PlatformExists
        self.platforms[entity.entity_name] = entity
        logger.success(f"{entity.entity_name} successfully registered to {self.name}")

    def add_mission(self,
                    mission_name:str,
                    summary:str,
                    title:str,
                    platform_name:str,
                    trajectory_path:str,
                    excess_space: int = 0.5,
                    extra_depth: int = 100,
                    crs: str = 'EPSG:4326',
                    vertical_crs: str = 'EPSG:5831',
                    creator:Creator = Creator(),
                    contributor:Contributor = Contributor(),
                    publisher:Publisher = Publisher(),
                    source_location: str = "CMEMS",
                    mission_time_step: int = 1,
                    apply_obs_error: bool = False,
                    standard_name_vocabulary: str = "https://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html",
                    ) -> None:
        """
        Add an auv mission to the campaign.
        Parameters
        ----------
        summary: str, required
            summary of mission
        platform_name: str, required
            name of the platform to use in the mission
        mission_name: str, required
            name of the mission
        title: str, required
            title of the mission
        trajectory_path: str, required
            path to auv trajectory netcdf/csv file
        standard_name_vocabulary: str, optional
            url of standard name vocabulary
        apply_obs_error: bool, optional
            apply an observation error to the payload to make more realistic observations
        mission_time_step: int, optional
            time step mission will run at, e.g. the output timestep of the payload and flight
        source_location: str, optional
            what model source to use, converts to a SourceType
        crs: str, optional
            Which CRS to use for geospatial coordinates
        vertical_crs: str, optional
            which vertical CRS to use for elevations
        contributor: Contributor, optional
            Contributor object
        publisher: Publisher, optional
            Publisher object
        creator: Creator, optional
            Creator object
        excess_space: float, optional
            amount of excess space to add to model/world download in decimal degrees
        extra_depth: int, optional
            amount of excess depth to add to model/world download in metres

        Raises
        ------
        MissionExists
            Mission name must not already be registered
        UnknownPlatform
            Platform must be registered

        """
        if mission_name in self.missions:
            logger.error(f"mission {mission_name} already exists")
            raise MissionExists
        try:
            platform_n = self.platforms[platform_name]
        except KeyError:
            raise UnknownPlatform
        mission_source = SourceConfig.from_string(source_location)
        mission = Mission.for_campaign(mission=mission_name,
                          title=title,
                          summary=summary,
                          platform_attributes=platform_n,
                          trajectory_path=trajectory_path,
                          creator=creator,
                          publisher=publisher,
                          contributor=contributor,
                          excess_space=excess_space,
                          extra_depth=extra_depth,
                          crs = crs,
                          vertical_crs = vertical_crs,
                          source_config=mission_source,
                          mission_time_step=mission_time_step,
                          apply_obs_error=apply_obs_error,
                          standard_name_vocabulary=standard_name_vocabulary
                          )
        interpolator = Interpolators()
        self.missions[mission.attrs.mission] = mission
        self.interpolators[mission.attrs.mission] = interpolator
        logger.success(f"successfully added mission {mission.attrs.mission} to campaign {self.name}")

    def build_missions(self) -> None:
        """
        Build the missions contained within the missions dictionary.
        """
        logger.info(f"building {self.name} missions")
        for mission in self.missions.values():
            logger.info(f"building {mission.attrs.mission}")

            self.catalog.init_catalog(source_type=mission.attrs.source_config.source_type)

            mission.build_mission(cat=self.catalog)
            logger.success(f"successfully built {mission.attrs.mission}")
        for key, interpol in self.interpolators.items():
            logger.info(f"building interpolators for {key}")
            interpol.build(worlds=self.missions[key].worlds,mission=key,source_type=self.missions[key].attrs.source_config.source_type)
            logger.success(f"successfully built interpolators for {key}")

    def enable_interpolator_cache(self) -> None:
        """
        enable interpolator cache so generated interpolators are stored on disk
        """
        for key, interpol in self.interpolators.items():
            interpol.cache = True
            logger.info(f"enabled interpolator cache for {key}")

    def run(self) -> None:
        """
        Executes the missions as specified within the mission's dictionary.
        """
        logger.info(f"running {self.name}")
        for mission in self.missions.values():
            logger.info(f"flying {mission.attrs.mission}")
            mission.fly(self.interpolators[mission.attrs.mission])
        logger.success(f"{self.name} finished successfully")

    def export(self,overwrite=True,export_path=None) -> None:
        """
        Exports the campaign object as a zarr group

        Parameters
        -----------
        overwrite: bool, optional
            overwrite any existing campaign store
        export_path: str, optional
            override default location of campaign store export.
        """
        campaign_name = self.name.replace(" ","_")
        logger.info(f"exporting {self.name}")
        if export_path is None:
            logger.info(f"creating zarr store at {campaign_name}.zarr")
            export_path = f"{campaign_name}.zarr"
        else:
            logger.info(f"exporting zarr store at {export_path}{sep}{campaign_name}.zarr")
        store = zarr.storage.LocalStore(f"{export_path}")
        logger.info(f"creating zarr group {self.name} in store")
        camp = zarr.group(store=store,overwrite=overwrite)
        camp.attrs['name'] = self.name
        camp.attrs['description'] = self.description
        #camp.attrs['uuid'] = str(self.uuid)
        logger.info(f"zarr group {self.name} successfully created")

        for key1, mission in self.missions.items():
            logger.info(f"creating zarr group for mission {mission.attrs.mission}")
            camp.create_group(mission.attrs.mission)
            logger.info(f"exporting {mission.attrs.mission}")
            mission.export_as_zarr(store=store)
            logger.info(f"successfully exported {mission.attrs.mission}")
        logger.success(f"successfully exported {self.name}")

