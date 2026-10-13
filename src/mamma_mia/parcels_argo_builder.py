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
# Define the new Kernel that mimics Argo vertical movement
import tomllib
from datetime import timedelta

import matplotlib.pyplot as plt
import numpy as np
import parcels
import parcels.tutorial

from mamma_mia.argo_kernel import ArgoVerticalMovement


def simulate(spec_file:str):

    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]

    mindepth = spec["kernel_parameters"]["mindepth"]

    # Load the GlobCurrent data in the Agulhas region from the example_data
    ds_fields = parcels.tutorial.open_dataset(
        "CopernicusMarine_data_for_Argo_tutorial/data"
    )

    # Select fields
    fields = {
        "U": ds_fields[spec["sensors"]["u_velocity"]["variable_name"]],
        "V": ds_fields[spec["sensors"]["v_velocity"]["variable_name"]],
    }

    # Convert to SGRID-compliant dataset and create FieldSet
    ds_fset = parcels.convert.copernicusmarine_to_sgrid(fields=fields)
    fieldset = parcels.FieldSet.from_sgrid_conventions(ds_fset)
    fieldset.to_windowed_arrays()

    # Add each configuration parameter as a constant
    fieldset.add_context('mindepth', mindepth)
    fieldset.add_context('driftdepth', spec["kernel_parameters"]['driftdepth'])
    fieldset.add_context('maxdepth', spec["kernel_parameters"]['maxdepth'])
    fieldset.add_context('vertical_speed', spec["kernel_parameters"]['vertical_speed'])
    fieldset.add_context('cycletime', spec["kernel_parameters"]['cycletime'])
    fieldset.add_context('drifttime', spec["kernel_parameters"]['drifttime'])

    # Define a new Particle type including extra Variables
    ArgoParticle = parcels.Particle.add_variable(
        [
            parcels.Variable("cycle_phase", dtype=np.int32, initial=0.0),
            parcels.Variable("cycle_age", dtype=np.float32, initial=0.0),
            parcels.Variable("drift_age", dtype=np.float32, initial=0.0),
        ]
    )

    # Initiate Argo floats in the Agulhas Current
    pset = parcels.ParticleSet(
        fieldset=fieldset,
        pclass=ArgoParticle,
        x=spec['mission_parameters']['lon_ini'],
        y=spec['mission_parameters']['lat_ini'],
        z=[mindepth, mindepth, mindepth],
    )

    # combine Argo vertical movement kernel with built-in Advection kernel
    kernels = [ArgoVerticalMovement, parcels.kernels.AdvectionRK4]

    if spec['mission_parameters']['overwrite']:
        mode = 'w'
    else:
        mode = None

    # Create a ParticleFile object to store the output
    output_file = parcels.ParticleFile(
        spec['mission_parameters']['output_file'],
        outputdt=timedelta(minutes=spec['mission_parameters']['timedelta']),
        mode=mode
    )

    # Now execute the kernels 
    pset.execute(
        kernels,
        runtime=timedelta(days=spec['mission_parameters']['runtime']),
        dt=timedelta(minutes=spec['mission_parameters']['output_timedelta']),
        output_file=output_file,
    )

def plot_diagnostic(spec_file:str):

    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]

    df = parcels.read_particlefile(spec['mission_parameters']['output_file'])
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
