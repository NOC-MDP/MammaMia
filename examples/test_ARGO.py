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
from pydantic import IPvAnyInterface

from mamma_mia import (
    add_missions,
    create_campaign,
    create_interpolator,
    create_mission,
    create_platform,
    create_trajectory,
    fly,
    get_data,
    plot_path,
    start_payload_dashboard,
)

ds = xr.open_zarr("../argo_float.zarr")
spec_file = "spec_files/argo_spec.toml"
missions = []
for i in range(ds["trajectory"].__len__()):
    ds_single_traj = ds.isel(trajectory=i)

    traj = create_trajectory(spec_file=spec_file, ds=ds_single_traj)
    platform = create_platform(spec_file=spec_file)

    # create mission using trajectory and platform datasets
    # a payload dataset is created but is currently empty
    missions.append(
        create_mission(
            mission_name="Example ARGO",
            summary="Virtual argo float mission",
            platform=platform,
            trajectory=traj,
            apply_obs_error=True,
        )
    )
    # get data from specified souce in spec file
    # note mission is returned with locations of data stored as attributes
    missions[i] = get_data(mission=missions[i])

    # create interpolators from downloaded datasets
    interpolator = create_interpolator(mission=missions[i])

    # fly the mission by interpolating the downloaded data onto the payload dataset
    missions[i] = fly(mission=missions[i], interpolators=interpolator)

# create a campaign to store the mission (missions can be standalone)
campaign = create_campaign(
    campaign_name="Argo mission",
    description="Argo float simulation",
)
campaign = add_missions(campaign=campaign, missions=missions)
# export to zarr (netcdf should be possible too)
campaign.to_zarr("ARGO.zarr", "w", consolidated=False)
# simple plot to show payload path
plot_path(mission=missions[0])
# plot a mission payload
start_payload_dashboard(mission=missions[0])
