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

from mamma_mia import Campaign
from mamma_mia import inventory

print("<=========> starting Mamma Mia ARGO Campaign test run <===========>")
print(f"Available groups in inventory {inventory.list_inventory_groups()}")
print(f"Available platform types: {inventory.list_platform_types()}")
# create campaign
campaign = Campaign(name="ARGO example drifter mission",
                    description="single ARGO APEX drifter",
                    verbose=True,
                    )
# create platform entity (mutable)
APEXY = inventory.create_platform_entity(entity_name="APEXY",platform_model="APEX",serial_number="APEX1")

# register sensor to platform
APEXY.register_sensor(sensor_type="CTD")
# register platform to the campaign for use in missions
campaign.register_platform(entity=APEXY)

# # # add mission
campaign.add_mission(mission_name="ARGO_01",
                     title="Example ARGO deployment",
                     summary="single ARGO deployed",
                     platform_name="APEXY",
                     trajectory_path="argo_float.zarr",
                     source_location="CMEMS",
                     mission_time_step=60,
                     apply_obs_error=True)

# Set interpolators to automatically cache as dat files (no need to regenerate them, useful for large worlds)
#campaign.enable_interpolator_cache()

# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()

# run/fly missions
campaign.run()

# visualise the results
campaign.missions["ARGO_01"].plot_trajectory()
campaign.missions["ARGO_01"].show_payload()
campaign.export()
print("the end")

