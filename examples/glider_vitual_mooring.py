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

spec_file = "spec_files/glider_spec_virtual_mooring.toml"
traj = create_trajectory(spec_file=spec_file)
platform = create_platform(spec_file=spec_file)

# create mission using trajectory and platform datasets
# a payload dataset is created but is currently empty
mission = create_mission(
    mission_name="Example Glider RAPID",
    summary="Virtual glider performing mooring replacement mission at RAPID",
    platform=platform,
    trajectory=traj,
    apply_obs_error=True,
)
# get data from specified souce in spec file
# note mission is returned with locations of data stored as attributes
mission = get_data(mission=mission)

# create interpolators from downloaded datasets
interpolator = create_interpolator(mission=mission)

# fly the mission by interpolating the downloaded data onto the payload dataset
mission = fly(mission=mission, interpolators=interpolator)

# create a campaign to store the mission (missions can be standalone)
campaign = create_campaign(
    campaign_name="RAPID virtual mooring",
    description="single glider performing virtual mooring",
)
campaign = add_mission(campaign=campaign, mission=mission)
# export to zarr (netcdf should be possible too)
campaign.to_zarr("RAPID.zarr", "w", consolidated=False)
# simple plot to show payload path
plot_path(missions=mission)
# plot a mission payload
start_payload_dashboard(missions=mission)
