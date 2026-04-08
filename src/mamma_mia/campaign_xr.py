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

import xarray as xr
from loguru import logger


def create_campaign(
    *missions: xr.DataTree, campaign_name: str = "campaign"
) -> xr.DataTree:
    children = {f"mission_{i}": mission for i, mission in enumerate(missions)}
    children["/"] = xr.Dataset(attrs={"campaign": campaign_name})

    campaign = xr.DataTree.from_dict(children)
    logger.success(f"campaign {campaign_name} created successfully")
    return campaign
