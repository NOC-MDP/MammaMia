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

from mamma_mia.campaign_xr import add_missions, create_campaign
from mamma_mia.get_data_xr import get_data
from mamma_mia.interpolator_xr import create_interpolator
from mamma_mia.mission_xr import create_mission, fly
from mamma_mia.platform_xr import create_platform
from mamma_mia.plot_xr import plot_path, start_payload_dashboard
from mamma_mia.trajectory_xr import create_trajectory

spec_file = "glider_spec.toml"
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
campaign = add_missions(campaign=campaign, missions=[mission])
# export to zarr (netcdf should be possible too)
campaign.to_zarr("BIO_ALR4.zarr", "w", consolidated=False)
# simple plot to show payload path
plot_path(mission=mission)
# plot a mission payload
start_payload_dashboard(mission=mission)
