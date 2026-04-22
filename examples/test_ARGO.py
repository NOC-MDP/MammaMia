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


from mamma_mia import (
    add_mission,
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

spec_file = "spec_files/argo_spec.toml"
trajectories = create_trajectory(spec_file=spec_file)
platform = create_platform(spec_file=spec_file)
missions = create_mission(
    platform=platform,
    trajectory=trajectories,
    mission_name="Example ARGO",
    summary="Virtual argo float mission",
    apply_obs_error=True,
)

missions = get_data(mission=missions)
interpolators = create_interpolator(mission=missions)

missions = fly(mission=missions, interpolators=interpolators)

# create a campaign to store the mission (missions can be standalone)
campaign = create_campaign(
    campaign_name="Argo mission",
    description="Argo float simulation",
)
campaign = add_mission(campaign=campaign, mission=missions)
# export to zarr (netcdf should be possible too)
campaign.to_zarr("ARGO.zarr", "w", consolidated=False)
# simple plot to show payload path

plot_path(mission=missions[0])
# plot a mission payload
start_payload_dashboard(mission=missions[0])
