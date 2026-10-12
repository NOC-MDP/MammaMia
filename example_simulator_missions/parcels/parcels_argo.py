# Define the new Kernel that mimics Argo vertical movement
from datetime import timedelta
import tomllib
import numpy as np
import parcels
import parcels.tutorial
from mamma_mia import ArgoVerticalMovement

spec_file = "argo_sim_spec.toml"

with open(spec_file, "rb") as f:
    raw = tomllib.load(f)
spec = raw["specification"]

mindepth = spec["argosim"]["kernel_parameters"]["mindepth"]

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
