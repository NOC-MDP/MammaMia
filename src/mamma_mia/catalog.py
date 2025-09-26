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

from attrs import define, field
import intake
import copernicusmarine
from loguru import logger


@define
class Cats:
    """
    Catalog class, contains all the model source data that is available to download. There is a field for each source,
    these are populated with their relevant catalogs that can be searched for matching worlds.

    Args:
        search: string that overrides the default search term used for CMEMS sources
        cat_path: string that overrides the default catalog location used for MSM sources
        overwrite: bool that overwrites the metadata cache used for CMEMS sources

    Returns:
        Populated Cats object
    """
    cmems_cat: copernicusmarine.CopernicusMarineCatalogue = None
    msm_cat: intake.Catalog = None
    search: str = "Global"
    cat_path: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk/mamma-mia/catalog/catalog.yml"
    overwrite: bool = False
    sources: dict = {"CMEMS": 1, "MSM": 2}

    def init_catalog(self):
        if self.cmems_cat is None:
            self.cmems_cat = copernicusmarine.describe(contains=[])
        if self.msm_cat is None:
            self.msm_cat = intake.open_catalog(self.cat_path)

    def get_sources_list(self):
        """
        list of model sources that can be downloaded to use within Mamma Mia along with their priority
        Returns: list of available world sources

        """
        return self.sources

    def set_priority(self, source: str, priority: int):
        """
        Sets the priority of a given source
        Returns:

        """
        self.sources[source] = priority
        logger.success(f"Set priority of {source} to {priority}")
