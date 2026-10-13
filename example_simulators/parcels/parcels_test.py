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

from mamma_mia import parcels_argo_builder as pab

# three argo floats in the Agulhas simulation specification
spec_file = "argo_sim_spec.toml"

argo_mission = pab.simulate(spec_file=spec_file)
pab.plot_diagnostic(spec_file=spec_file)

