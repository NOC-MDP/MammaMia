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
import json
import os
from datetime import datetime

from attrs import define
from OceanDataStore import OceanDataCatalog
import copernicusmarine
from loguru import logger
import jsonpickle
from mamma_mia.worlds import SourceType
from pathlib import Path


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
            self.cmems_cat = copernicusmarine.describe(contains=[])
        elif source_type == SourceType.MSM:
            logger.info("MSM source requested, building catalog")
            cat_file = Path("catalog.json")
            if cat_file.is_file() and not self.overwrite:
                logger.info("local catalog file found, reading catalog")
                with open(cat_file, "r") as f:
                    cat = json.load(f)
                self.msm_cat = jsonpickle.decode(cat)
                cat = OceanDataCatalog(catalog_name="noc-model-stac")
                last_update_server = datetime.strptime(cat.Catalog.extra_fields['last_update'],"%Y-%m-%dT%H:%M:%S.%f")
                last_update_local = datetime.strptime(self.msm_cat.Catalog.extra_fields['last_update'],"%Y-%m-%dT%H:%M:%S.%f")
                if last_update_local < last_update_server:
                    logger.info("local catalog is out of date with server catalog, updating....")
                    self.__create_local_catalog()
                    logger.info("local catalog updated")
            else:
                if self.overwrite:
                    logger.info("catalog overwrite requested, creating new catalog")
                else:
                    logger.info("local catalog not found, creating new catalog")
                self.__create_local_catalog()

        logger.info("Catalog initialized")

    def __create_local_catalog(self,file_name="catalog.json"):
        self.msm_cat = OceanDataCatalog(catalog_name="noc-model-stac")
        self.msm_cat.search(collection="noc-npd-era5")
        cat_file2 = jsonpickle.encode(self.msm_cat)
        with open(file_name, "w") as f2:
            json.dump(cat_file2, f2)
