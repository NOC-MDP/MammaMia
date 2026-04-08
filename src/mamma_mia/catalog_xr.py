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
from datetime import datetime
from pathlib import Path

import jsonpickle
from copernicusmarine import CopernicusMarineCatalogue, describe
from loguru import logger
from OceanDataStore import OceanDataCatalog


def __create_local_catalog(file_name="catalog.json"):
    catalog = OceanDataCatalog(catalog_name="noc-model-stac")
    catalog.search(collection="noc-npd-era5")
    cat_file2 = jsonpickle.encode(catalog)
    with open(file_name, "w") as f2:
        json.dump(cat_file2, f2)
    return catalog


def create_catalog(
    source: str, overwrite: bool = False
) -> str | CopernicusMarineCatalogue | OceanDataCatalog:
    if source == "CMEMS":
        catalog = describe(contains=[])
    elif source == "NOC":
        cat_file = Path("catalog.json")
        if cat_file.is_file() and not overwrite:
            logger.info("local catalog file found, reading catalog")
            with open(cat_file, "r") as f:
                cat = json.load(f)
            catalog = jsonpickle.decode(cat)
            cat = OceanDataCatalog(catalog_name="noc-model-stac")
            last_update_server = datetime.strptime(
                cat.Catalog.extra_fields["last_update"], "%Y-%m-%dT%H:%M:%S.%f"
            )
            last_update_local = datetime.strptime(
                catalog.Catalog.extra_fields["last_update"], "%Y-%m-%dT%H:%M:%S.%f"
            )
            if last_update_local < last_update_server:
                logger.info(
                    "local catalog is out of date with server catalog, updating...."
                )
                catalog = __create_local_catalog()
                logger.info("local catalog updated")
        else:
            if overwrite:
                logger.info("catalog overwrite requested, creating new catalog")
            else:
                logger.info("local catalog not found, creating new catalog")
            catalog = __create_local_catalog()
    else:
        logger.info(f"assuming local data source at location: {source}")
        catalog = source

    return catalog
