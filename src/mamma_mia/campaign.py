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
    missions: list[xr.DataTree] | None = None,
    campaign_name: str = "campaign",
    description: str = "",
) -> xr.DataTree:
    """
    Create a campaign DataTree from zero or more mission DataTrees.

    Parameters
    ----------
    missions : list[xr.DataTree] | None
        Zero or more mission DataTrees. Pass None or omit to create an empty campaign.
    campaign_name : str
        Name stored in the root dataset's 'campaign' attribute.
    description : str
        Optional human-readable description stored in the root dataset's
        'description' attribute.

    Returns
    -------
    xr.DataTree
        A DataTree whose root carries campaign-level attributes and whose
        children are the supplied missions.
    """
    missions = missions or []
    children: dict[str, xr.DataTree | xr.Dataset] = {
        mission.attrs["mission_attrs"]["name"]: mission for mission in missions
    }
    children["/"] = xr.Dataset(
        attrs={"campaign": campaign_name, "description": description}
    )
    campaign = xr.DataTree.from_dict(children)
    logger.success(f"Campaign '{campaign_name}' created successfully")
    return campaign


def add_missions(
    campaign: xr.DataTree,
    missions: list[xr.DataTree],
) -> xr.DataTree:
    """
    Append one or more mission DataTrees to an existing campaign.

    Parameters
    ----------
    campaign : xr.DataTree
        A campaign DataTree previously created by ``create_campaign``.
    missions : list[xr.DataTree]
        One or more mission DataTrees to add.

    Returns
    -------
    xr.DataTree
        The updated campaign DataTree.

    Raises
    ------
    ValueError
        If an empty list is supplied.
    """
    if not missions:
        raise ValueError("At least one mission must be supplied.")

    updated: dict[str, xr.DataTree | xr.Dataset] = dict(campaign.children)
    updated["/"] = campaign.ds  # preserve root attributes
    for mission in missions:
        updated[mission.attrs["mission_attrs"]["name"]] = mission

    campaign_name = campaign.attrs.get("campaign", "campaign")
    updated_campaign = xr.DataTree.from_dict(updated)
    logger.success(f"Added {len(missions)} mission(s) to campaign '{campaign_name}'")
    return updated_campaign
