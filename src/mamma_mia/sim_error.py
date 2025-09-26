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

import numpy as np
from loguru import logger

def simulate_sensor_error(model_t,
                                mission_ts,
                                accuracy_bias,
                                resolution,
                                drift_per_month,
                                m_min, m_max,
                                percent_errors,
                                noise_std):
    """
    Simulate synthetic temperature observations from model truth.
    Applies:
    - bias based on accuracy
    - noise
    - drift per month

    Parameters:
    - model_t: array of model "true" sensor values
    - mission_ts: mission time step (seconds)
    - accuracy_bias: max absolute bias error (±value)
    - noise_std: std of random noise (instrumental)
    - resolution: sensor resolution (quantization step)
    - drift_per_month: long-term drift in unit/month
    - m_min, m_max: valid measurement range
    - percent: if true all error values are % of sensor range
    """
    if accuracy_bias == -999.999 or resolution == -999.999 or drift_per_month == -999.999 or m_min == -999.999 or m_max == -999.999 or noise_std == -999.999:
        logger.warning("null values set in sensor specification no obs error applied")
        return model_t
    model_t = np.asarray(model_t)
    shape = model_t.shape
    range_span = m_max - m_min

    if percent_errors:
        accuracy_bias *= range_span
        noise_std *= range_span
        resolution *= range_span
        drift_per_month *= range_span

    # 1. Bias (systematic error)
    bias = np.random.uniform(-accuracy_bias, accuracy_bias)

    # 2. Random noise
    noise = np.random.normal(0, noise_std, size=shape)

    # 3. Drift (computed from timestep and sample index)
    # Convert timestep to days
    timestep_days = mission_ts / (60 * 60 * 24)

    # Create time array: assumes last axis is time (standard for time-series)
    time_steps = np.arange(shape[-1]) * timestep_days
    time_days = np.broadcast_to(time_steps, shape)  # match shape of model_T

    drift_rate = drift_per_month / 30.0  # drift per day
    drift = drift_rate * time_days

    # 4. Combine all
    obs = model_t + bias + noise + drift

    # 5. Quantization
    obs = np.round(obs / resolution) * resolution

    # 6. Clipping
    obs = np.clip(obs, m_min, m_max)

    return obs