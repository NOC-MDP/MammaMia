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
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import parcels
import datetime as dt
import os
import shutil
import pathlib
from mamma_mia.argo_kernel import ArgoVerticalMovement
from mamma_mia.get_data import get_parcels_data


def simulate(spec_file:str):

    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]

    mindepth = spec["kernel_parameters"]["mindepth"]

    # download data to cache and get their paths
    dataset_paths = get_parcels_data(sensors=spec['sensors'], geospatial_attrs=spec['environment']['extent'])

    # Cache to avoid reopening the same Zarr store multiple times
    opened_stores = {}
    datasets = []

    for field_name, params in dataset_paths.items():
        store_path = params['store']
        var_name = params['variable_name']
        
        # Open the zarr dataset if not already loaded
        if store_path not in opened_stores:
            opened_stores[store_path] = xr.open_dataset(store_path, engine='zarr')
        
        # Extract the variable and rename it to the dictionary key
        da = opened_stores[store_path][var_name].rename(field_name)
        datasets.append(da)

    # Merge into a single xarray.Dataset emulating ds_fields
    ds_fields = xr.merge(datasets)

    # Select fields
    fields = {
        "U": ds_fields["u_velocity"],
        "V": ds_fields["v_velocity"],
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
    datetime_list = [dt.datetime.strptime(d, "%Y-%m-%dT%H:%M:%SZ") for d in spec['mission_parameters']['datetime_start']]
    # Initiate Argo floats in the Agulhas Current
    pset = parcels.ParticleSet(
        fieldset=fieldset,
        pclass=ArgoParticle,
        x=spec['mission_parameters']['lon_ini'],
        y=spec['mission_parameters']['lat_ini'],
        z=spec['mission_parameters']['depth_ini'],
        t=datetime_list
    )

    # combine Argo vertical movement kernel with built-in Advection kernel
    kernels = [ArgoVerticalMovement, parcels.kernels.AdvectionRK4]

    if spec['mission_parameters']['overwrite']:
        mode = 'w'
    else:
        mode = None

    zarr_output_file = f"{spec['mission_parameters']['output_file']}"
    parcels_temp_file = "parcels_tmp.parquet"

    # Create a ParticleFile object to store the output
    output_file = parcels.ParticleFile(
        parcels_temp_file,
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
    # TODO due to the high memory requirements, this should probably improved by handling parquet files directly rather than this hack to get v3 compatible zarrs
    # 2. Convert the parquet file into a v3-format Zarr store
    zarr_path = pathlib.Path(zarr_output_file)
    # Remove the existing Zarr directory if it already exists
    if zarr_path.exists():
        shutil.rmtree(zarr_path)
    parcels.particlefile_to_v3_zarr(
    from_parquet=pathlib.Path(parcels_temp_file),
    to_zarr=pathlib.Path(zarr_output_file)
)
    os.remove(parcels_temp_file)


def plot_diagnostic(spec_file: str):

    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]

    # Open the v3 Zarr store directly with xarray
    ds = xr.open_zarr(spec['mission_parameters']['output_file'])

    # --- 2D Plot (Time vs Depth) ---
    fig = plt.figure(figsize=(13, 6))
    ax = plt.axes()
    
    for i in range(ds.dims["trajectory"]):
        t = ds.time.isel(trajectory=i).values
        z = ds.z.isel(trajectory=i).values
        
        valid = ~np.isnan(z)
        ax.plot(t[valid], z[valid], alpha=0.6)

    ax.set_xlabel("Time")
    ax.set_ylabel("Depth (m)")
    ax.invert_yaxis()
    plt.show()

    # --- 3D Plot (Longitude, Latitude, Depth) ---
    fig = plt.figure(figsize=(13, 8))
    ax = plt.axes(projection="3d")
    ax.view_init(azim=-145)
    
    for i in range(ds.dims["trajectory"]):
        x = ds.lon.isel(trajectory=i).values
        y = ds.lat.isel(trajectory=i).values
        z = ds.z.isel(trajectory=i).values
        
        valid = ~np.isnan(z)
        ax.plot3D(x[valid], y[valid], z[valid], alpha=0.6)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_zlabel("Depth (m)")
    
    # Compute the max depth safely by evaluating the Dask array into a scalar float
    max_z = float(ds.z.max().values)
    ax.set_zlim(max_z, 0)
    
    plt.show()