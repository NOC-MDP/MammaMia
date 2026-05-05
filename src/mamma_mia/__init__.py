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
from mamma_mia.campaign import add_mission, create_campaign
from mamma_mia.fly import fly
from mamma_mia.get_data import get_data, get_extent
from mamma_mia.interpolator import create_interpolator, interpolate
from mamma_mia.mission import create_mission
from mamma_mia.mission_builder import (
    run_mission,
    save_mission,
    simulate,
)
from mamma_mia.platform import create_platform
from mamma_mia.plot import plot_path, start_payload_dashboard
from mamma_mia.trajectory import create_trajectory

__all__ = [
    "create_campaign",
    "add_mission",
    "create_mission",
    "fly",
    "get_data",
    "create_interpolator",
    "run_mission",
    "save_mission",
    "simulate",
    "create_platform",
    "plot_path",
    "start_payload_dashboard",
    "create_trajectory",
    "get_extent",
    "interpolate",
]
