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

from mamma_mia.campaign_xr import create_campaign
from mamma_mia.get_data_xr import get_data
from mamma_mia.interpolator_xr import create_interpolator
from mamma_mia.mission_xr import create_mission, fly
from mamma_mia.platform_xr import create_platform
from mamma_mia.plot_xr import plot_payload, plot_trajectory
from mamma_mia.trajectory_xr import create_trajectory

spec_file = "glider_spec.toml"
traj = create_trajectory(spec_file=spec_file)
platform = create_platform(spec_file=spec_file)

mission = create_mission(
    mission_name="test", summary="testy mctestface", platform=platform, trajectory=traj
)
mission = get_data(mission=mission)

interpolator = create_interpolator(mission=mission)

mission = fly(mission=mission, interpolators=interpolator)

campaign = create_campaign(mission, mission, campaign_name="test")

campaign.to_zarr("test.zarr", "w")

plot_payload(mission=mission)
plot_trajectory(mission=mission)
