# Define the new Kernel that mimics Argo vertical movement
from datetime import timedelta

import numpy as np
import parcels
import parcels.tutorial

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

# Define the new Kernel that mimics Argo vertical movement
mindepth = 1.0  # minimum depth in m
driftdepth = 1000  # maximum drift depth in m
maxdepth = 2000  # maximum depth in m
vertical_speed = 0.10  # sink and rise speed in m/s
cycletime = 10 * 86400  # total time of cycle in seconds
drifttime = 9 * 86400  # time of deep drift in seconds

# Load the GlobCurrent data in the Agulhas region from the example_data
ds_fields = parcels.tutorial.open_dataset(
    "CopernicusMarine_data_for_Argo_tutorial/data"
)

# Select fields
fields = {
    "U": ds_fields["uo"],
    "V": ds_fields["vo"],
}

# Convert to SGRID-compliant dataset and create FieldSet
ds_fset = parcels.convert.copernicusmarine_to_sgrid(fields=fields)
fieldset = parcels.FieldSet.from_sgrid_conventions(ds_fset)
fieldset.to_windowed_arrays()

# Define a new Particle type including extra Variables
ArgoParticle = parcels.Particle.add_variable(
    [
        parcels.Variable("cycle_phase", dtype=np.int32, initial=0.0),
        parcels.Variable("cycle_age", dtype=np.float32, initial=0.0),
        parcels.Variable("drift_age", dtype=np.float32, initial=0.0),
    ]
)

# Initiate three Argo floats in the Agulhas Current
pset = parcels.ParticleSet(
    fieldset=fieldset,
    pclass=ArgoParticle,
    x=[32, 32.1, 32],
    y=[-31, -31, -30.9],
    z=[mindepth, mindepth, mindepth],
)

# combine Argo vertical movement kernel with built-in Advection kernel
kernels = [ArgoVerticalMovement, parcels.kernels.AdvectionRK4]

# Create a ParticleFile object to store the output
output_file = parcels.ParticleFile(
    "argo_float.parquet",
    outputdt=timedelta(minutes=15),
    mode='w'
)

# Now execute the kernels for 30 days, saving data every 30 minutes
pset.execute(
    kernels,
    runtime=timedelta(days=30),
    dt=timedelta(minutes=15),
    output_file=output_file,
)

import matplotlib.pyplot as plt

df = parcels.read_particlefile("argo_float.parquet")
fig = plt.figure(figsize=(13, 6))
ax = plt.axes()
# Group by particle_id and plot each particle's trajectory separately
for particle_id, group in df.group_by("particle_id"):
  ax.plot(group["t"], group["z"], alpha=0.6)

# cb = ax.scatter(df["t"], df["z"], s=20, marker="o", zorder=2)
ax.set_xlabel("Time [days]")
ax.set_ylabel("Depth (m)")
ax.invert_yaxis()
# fig.colorbar(cb, label="Time?")
plt.show()

from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(13, 8))
ax = plt.axes(projection="3d")
ax.view_init(azim=-145)
# Group by particle_id and plot each particle's trajectory separately
for particle_id, group in df.group_by("particle_id"):
    ax.plot3D(group["x"], group["y"], group["z"], alpha=0.6)
# cb = ax.scatter(df["x"], df["y"], df["z"], s=20, marker="o", zorder=2)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_zlabel("Depth (m)")
ax.set_zlim(df["z"].max(), 0)
# fig.colorbar(cb, label="Time?")
plt.show()
