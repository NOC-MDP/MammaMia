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


def simulate_sensor_error(
    model_t,
    mission_ts: int,
    accuracy_bias: float,
    resolution: float,
    drift_per_month: float,
    m_min,
    m_max,
    percent_errors: bool,
    noise_std: float,
) -> np.ndarray:
    """
    Simulate synthetic sensor observations by applying error models to model truth values.

    Transforms an array of model truth values into realistic synthetic observations
    by sequentially applying bias, random noise, long-term drift, and quantization.
    Error magnitudes can be expressed either in absolute units or as a percentage of
    the sensor measurement range.

    Parameters
    ----------
    model_t : array-like
        Array of model truth values representing the idealised sensor signal.
    mission_ts : int
        Mission time step in seconds, used to accumulate drift over the
        observation period.
    accuracy_bias : float
        Maximum absolute bias error applied to the signal (±value). If
        ``percent_errors`` is True, interpreted as a percentage of the
        sensor range.
    resolution : float
        Sensor quantization step size. Observations are rounded to the nearest
        multiple of this value. If ``percent_errors`` is True, interpreted as
        a percentage of the sensor range.
    drift_per_month : float
        Long-term linear drift rate in sensor units per month. If
        ``percent_errors`` is True, interpreted as a percentage of the
        sensor range per month.
    m_min : float
        Lower bound of the valid sensor measurement range.
    m_max : float
        Upper bound of the valid sensor measurement range.
    percent_errors : bool
        If True, ``accuracy_bias``, ``noise_std``, ``resolution``, and
        ``drift_per_month`` are all treated as percentages of the sensor
        range (``m_max - m_min``) rather than absolute values.
    noise_std : float
        Standard deviation of the Gaussian random noise component. If
        ``percent_errors`` is True, interpreted as a percentage of the
        sensor range.

    Returns
    -------
    array-like
        Array of simulated sensor observations with bias, noise, drift, and
        quantization applied, clipped to the valid measurement range
        [``m_min``, ``m_max``].
    """
    if (
        accuracy_bias == -999.999
        or resolution == -999.999
        or drift_per_month == -999.999
        or m_min == -999.999
        or m_max == -999.999
        or noise_std == -999.999
    ):
        logger.warning("null values set in sensor specification no obs error applied")
        return model_t
    # model_t = np.asarray(model_t)
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
