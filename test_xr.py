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
from mamma_mia.get_model_xr import get_worlds
from mamma_mia.interpolator_xr import create_interpolator
from mamma_mia.mission_xr import create_mission
from mamma_mia.platform_xr import create_platform
from mamma_mia.trajectory_xr import create_trajectory

spec_file = "glider_spec.toml"
# tpath = "arctic_vis_traj.csv"
traj = create_trajectory(spec_file=spec_file)

platform = create_platform(spec_file=spec_file)
# if the platform uses NMEA_coords to store its position then these need to be converted into lat/lon
platform.attrs["NMEA_coordinates"] = True

mission = create_mission(
    mission_name="test", summary="testy mctestface", platform=platform, trajectory=traj
)

# mission = get_worlds(model_id="cmems_mod_glo_phy_anfc_0.083deg_PT1H-m", mission=mission)


campaign = create_campaign(mission, mission, campaign_name="test")


campaign.to_zarr("test.zarr", "w")
