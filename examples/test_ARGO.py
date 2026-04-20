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

from mamma_mia import (
    add_missions,
    create_campaign,
    create_interpolator,
    create_missions,
    create_platform,
    create_trajectories,
    fly,
    get_data,
    plot_path,
    start_payload_dashboard,
)

ds = xr.open_zarr("trajectories/argo_float.zarr")
spec_file = "spec_files/argo_spec.toml"
trajectories = create_trajectories(spec_file=spec_file)
platform = create_platform(spec_file=spec_file)
missions = create_missions(
    mission_name="Example ARGO",
    summary="Virtual argo float mission",
    platform=platform,
    trajectories=trajectories,
    apply_obs_error=True,
)
for i in range(missions.__len__()):
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
