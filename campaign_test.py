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


print(f"Available groups in inventory {inventory.list_inventory_groups()}")
print(f"Available platform types: {inventory.list_platform_types()}")
print(f"Available platform models: {inventory.list_platform_models()}")
print(f"Available parameters: {inventory.list_parameters()}")
print(f"Available sensor types: {inventory.list_sensor_types()}")
print(f"Parameters Alias: {inventory.list_parameter_aliases()}")
print(f"sensors available for platform Slocum G2: {inventory.list_sensors(platform_model='Slocum_G2')}")
print(f"sensors of type CTD: {inventory.list_sensors(sensor_type='CTD')}")
print(f"sensor info: {inventory.get_sensor_info(platform_model='APEX', sensor_type='CTD')}")

print("<=========> starting Mamma Mia AUV Campaign test run <===========>")
# create campaign
campaign = Campaign(name="RAPID array virtual mooring",
                    description="single slocum glider deployment at a RAPID mooring",
                    verbose=True,
                    )
# create platform entity (mutable)
Churchill = inventory.create_platform_entity(entity_name="Churchill",platform_model="Slocum_G2",serial_number="unit_398")

# register sensor to platform
Churchill.register_sensor(sensor_type="CTD")


# # # add mission
campaign.add_mission(mission_name="RAD24_01",
                     title="Churchill with CTD deployment at RAPID array mooring eb1l2n",
                     summary="single glider deployed to perform a virtual mooring flight at the eb1l2n RAPID array.",
                     platform=Churchill,
                     trajectory_path="data/RAPID-mooring/rapid-mooring.nc",
                     source_location="CMEMS",
                     mission_time_step=60,
                     apply_obs_error=True)

# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()

# run/fly missions
campaign.run()

# visualise the results
campaign.missions["RAD24_01"].plot_trajectory()
campaign.missions["RAD24_01"].show_payload()
campaign.export()
print("the end")

