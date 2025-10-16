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

from attrs import define
from OceanDataStore import OceanDataCatalog
import copernicusmarine
from loguru import logger

from mamma_mia.worlds import SourceType


@define
class Cats:
    """
    Catalog class, contains all the model source data that is available to download. There is a field for each source,
    these are populated with their relevant catalogs that can be searched for matching worlds.

    Parameters
    ----------
    overwrite: bool, optional
        overwrites the metadata cache used for CMEMS sources

    Attributes
    ----------
    cmems_cat: CopernicusMarineCatalog
        cmems catalog class
    msm_cat: OceanDataCatalog
        msm catalog class
    """
    cmems_cat: copernicusmarine.CopernicusMarineCatalogue = None
    msm_cat: OceanDataCatalog = None
    overwrite: bool = False

    def init_catalog(self,source_type: SourceType):
        """
        initialize the catalog class
        """
        logger.info("Initializing catalog")
        if source_type == SourceType.LOCAL:
            logger.info("local data source request, skipping catalog initialization")
        elif source_type == SourceType.CMEMS:
            logger.info("CMEMS source requested, building catalog")
            if self.cmems_cat is None:
                self.cmems_cat = copernicusmarine.describe(contains=[])
        elif source_type == SourceType.MSM:
            logger.info("CMEMS source requested, building catalog")
            if self.msm_cat is None:
                self.msm_cat = OceanDataCatalog(catalog_name="noc-model-stac")
                self.msm_cat.search()
        logger.info("Catalog initialized")

