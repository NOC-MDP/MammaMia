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

spec_files = [
    "spec_files/BIOCARBON/ALR4_649.toml",
    "spec_files/BIOCARBON/ALR6_650.toml",
    "spec_files/BIOCARBON/cabot_645.toml",
    # "spec_files/BIOCARBON/churchill_647.toml",
    "spec_files/BIOCARBON/doombar_648.toml",
    "spec_files/BIOCARBON/nelson_646.toml",
]
mission_names = [
    "ALR4_649",
    "ALR6_650",
    "cabot_645",
    # "churchill_647",
    "doombar_648",
    "nelson_646",
]
missions = []
interpolators = []
for i in range(spec_files.__len__()):
    traj = create_trajectory(spec_file=spec_files[i])
    platform = create_platform(spec_file=spec_files[i])

    # create mission using trajectory and platform datasets
    # a payload dataset is created but is currently empty
    missions.append(
        create_mission(
            mission_name=mission_names[i],
            summary=f"simulated payload for {mission_names[i]} trajectory in BIOCARBON campaign",
            platform=platform,
            trajectory=traj,
            mission_time_step=900,
            apply_obs_error=True,
        )
    )
    # get data from specified souce in spec file
    # note mission is returned with locations of data stored as attributes
    missions[i] = get_data(mission=missions[i])

    # create interpolators from downloaded datasets
    interpolators.append(create_interpolator(mission=missions[i]))

    # fly the mission by interpolating the downloaded data onto the payload dataset
    missions[i] = fly(mission=missions[i], interpolators=interpolators[i])

# create a campaign to store the mission (missions can be standalone)
campaign = create_campaign(
    campaign_name="BIOCARBON", description="BIOCARBON campaign from Iceland to UK"
)
campaign = add_mission(campaign=campaign, mission=missions)
# export to zarr (netcdf should be possible too)
campaign.to_zarr("BIOCARBON_2024.zarr", "w", consolidated=False)
# simple plot to show payload path
plot_path(missions=missions)
# plot a mission payload
start_payload_dashboard(missions=missions)
