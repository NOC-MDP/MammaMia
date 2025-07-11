
import numpy as np

def simulate_sensor_error(model_t,
                                mission_ts,
                                accuracy_bias=0.001,
                                resolution=0.0002,
                                drift_per_month=0.0002,
                                m_min=-5, m_max=40,
                                percent_errors=False):
    """
    Simulate synthetic temperature observations from model truth.

    Parameters:
    - model_t: array of model "true" temperature values
    - mission_ts: mission time step (seconds)
    - accuracy_bias: max absolute bias error (±value)
    - noise_std: std of random noise (instrumental)
    - resolution: sensor resolution (quantization step)
    - drift_per_month: long-term drift in °C/month
    - m_min, m_max: valid measurement range
    - percent: if true all error values are % of sensor range
    """

    model_t = np.asarray(model_t)
    shape = model_t.shape
    range_span = m_max - m_min
    # TODO assess if this is a sensible assumption
    # assume noise std is half the accuracy
    noise_std = accuracy_bias/2

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