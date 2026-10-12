try:
    import parcels
except ImportError as e:
    logger.debug(f"optional dependency glidersim is not installed: {e}")

# Define the new Kernel that mimics Argo vertical movement
mindepth = 1.0  # minimum depth in m
driftdepth = 1000  # maximum drift depth in m
maxdepth = 2000  # maximum depth in m
vertical_speed = 0.10  # sink and rise speed in m/s
cycletime = 10 * 86400  # total time of cycle in seconds
drifttime = 9 * 86400  # time of deep drift in seconds

@parcels.validate_kernel
def ArgoVerticalMovement(particles, fieldset):
    # Split particles based on their current cycle_phase
    ptcls0 = particles[particles.cycle_phase == 0]
    ptcls1 = particles[particles.cycle_phase == 1]
    ptcls2 = particles[particles.cycle_phase == 2]
    ptcls3 = particles[particles.cycle_phase == 3]
    ptcls4 = particles[particles.cycle_phase == 4]

    # Phase 0: Sinking with vertical_speed until depth is driftdepth
    ptcls0.dz += vertical_speed * ptcls0.dt
    next_phase = ptcls0.z + ptcls0.dz >= driftdepth
    ptcls0.cycle_phase[next_phase] = 1
    ptcls0.dz[next_phase] = driftdepth - ptcls0.z[next_phase]  # avoid overshoot

    # Phase 1: Drifting at depth for drifttime seconds
    ptcls1.drift_age += ptcls1.dt
    next_phase = ptcls1.drift_age >= drifttime
    ptcls1.cycle_phase[next_phase] = 2
    ptcls1.drift_age[next_phase] = 0  # reset drift_age for next cycle

    # Phase 2: Sinking further to maxdepth
    ptcls2.dz += vertical_speed * ptcls2.dt
    next_phase = ptcls2.z + ptcls2.dz >= maxdepth
    ptcls2.cycle_phase[next_phase] = 3
    ptcls2.dz[next_phase] = maxdepth - ptcls2.z[next_phase]  # avoid overshoot

    # Phase 3: Rising with vertical_speed until at surface
    ptcls3.dz -= vertical_speed * ptcls3.dt
    next_phase = ptcls3.z + ptcls3.dz <= mindepth
    ptcls3.cycle_phase[next_phase] = 4
    ptcls3.dz[next_phase] = mindepth - ptcls3.z[next_phase]  # avoid overshoot

    # Phase 4: Transmitting at surface until cycletime is reached
    next_phase = ptcls4.cycle_age >= cycletime
    ptcls4.cycle_phase[next_phase] = 0
    ptcls4.cycle_age[next_phase] = 0  # reset cycle_age for next cycle


    particles.cycle_age += particles.dt  # update cycle_age
