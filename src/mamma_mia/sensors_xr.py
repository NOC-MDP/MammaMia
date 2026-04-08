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

sensors = {
    "CTD": {
        "potential_temperature": {
            "accuracy": 0.001,
            "resolution": 0.001,
            "drift_per_month": 0.0002,
            "range": [-5, 42],
            "percent_errors": False,
            "noise_std": 0.0005,
            "alias": ["thetao"],
        },
        "practical_salinity": {
            "accuracy": 0.005,
            "resolution": 0.0001,
            "drift_per_month": 0.003,
            "range": [0, 42],
            "percent_errors": False,
            "noise_std": 0.0025,
            "aliases": ["so", "soce_abs", "so_abs"],
        },
        "pressure": {
            "accuracy": 0.1,
            "resolution": 0.002,
            "drift_per_month": 0.0042,
            "range": [0, 2000],
            "percent_errors": False,
            "noise_std": 0.0005,
            "aliases": ["sci_water_pressure", "PRESSURE"],
        },
    },
    "data_logger": {
        "latitude": {
            "accuracy": -999.999,
            "resolution": -999.999,
            "drift_per_month": -999.999,
            "range": [-999.999, -999.999],
            "percent_errors": False,
            "noise_std": -999.999,
            "aliases": ["m_lat", "nav_lat", "LATITUDE", "lat"],
        },
        "longitude": {
            "accuracy": -999.999,
            "resolution": -999.999,
            "drift_per_month": -999.999,
            "range": [-999.999, -999.999],
            "percent_errors": False,
            "noise_std": -999.999,
            "aliases": ["m_lon", "nav_lon", "LONGITUDE", "lon"],
        },
        "depth": {
            "accuracy": -999.999,
            "resolution": -999.999,
            "drift_per_month": -999.999,
            "range": [-999.999, -999.999],
            "percent_errors": False,
            "noise_std": -999.999,
            "aliases": ["m_depth", "GLIDER_DEPTH"],
        },
        "heading": {
            "accuracy": -999.999,
            "resolution": -999.999,
            "drift_per_month": -999.999,
            "range": [-999.999, -999.999],
            "percent_errors": False,
            "noise_std": -999.999,
            "aliases": ["m_yaw", "GLIDER_YAW"],
        },
        "roll": {
            "accuracy": -999.999,
            "resolution": -999.999,
            "drift_per_month": -999.999,
            "range": [-999.999, -999.999],
            "percent_errors": False,
            "noise_std": -999.999,
            "aliases": ["m_roll", "GLIDER_ROLL"],
        },
        "pitch": {
            "accuracy": -999.999,
            "resolution": -999.999,
            "drift_per_month": -999.999,
            "range": [-999.999, -999.999],
            "percent_errors": False,
            "noise_std": -999.999,
            "aliases": ["m_pitch", "GLIDER_PITCH"],
        },
        "time": {
            "accuracy": -999.999,
            "resolution": -999.999,
            "drift_per_month": -999.999,
            "range": [-999.999, -999.999],
            "percent_errors": False,
            "aliases": ["time", "TIME", "time_counter"],
        },
    },
}
