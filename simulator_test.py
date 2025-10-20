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

from mamma_mia import GliderMissionBuilder

virtual_mooring = GliderMissionBuilder.virtual_mooring(
    mission_name="rapid-mooring_spiral",
    datetime_str="2023-03-03T12:00:00:Z",
    description="RAPID ARRAY spiral simulation",
    glider_model="DEEP",
    inital_heading=225,
    lat_ini=27.225,
    lon_ini=-15.4225,
    glider_name="comet",
    mission_directory="RAPID-mooring_spiral",
    dive_depth=1000,
    spiral=False
)

virtual_mooring.run_mission(maxSimulationTime=2,verbose=True) # 2 days
virtual_mooring.save_mission()

waypoints = GliderMissionBuilder.follow_waypoints(
    mission_name="waypoints2",
    datetime_str="2023-03-03T12:00:00:Z",
    description="follow waypoints simulation",
    glider_model="DEEP",
    inital_heading=225,
    lat_ini=27.225,
    lon_ini=-15.4225,
    lat_wp=[27.425,27.825,28.205,28.503],
    lon_wp=[-15.4225,-15.4225,-15.4225,-15.4225],
    glider_name="comet",
    mission_directory="waypoints2",
    dive_depth=1000
)

waypoints.run_mission(maxSimulationTime=7,verbose=True) # 7 days
waypoints.save_mission()