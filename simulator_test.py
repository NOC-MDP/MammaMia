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

from mamma_mia import run_mission, save_mission, simulate

# virtual mooring simulation specification
spec_file = "example_simulator_missions/rapid_vm_sim_spec.toml"
# follow waypoints simulation specification
spec_file2 = "example_simulator_missions/rapid_wp_sim_spec.toml"

virtual_mooring = simulate(spec_file=spec_file)
run_mission(gm=virtual_mooring, spec_file=spec_file)
save_mission(gm=virtual_mooring, spec_file=spec_file)

follow_waypoints = simulate(spec_file=spec_file2)
run_mission(gm=follow_waypoints, spec_file=spec_file2)
save_mission(gm=follow_waypoints, spec_file=spec_file2)
