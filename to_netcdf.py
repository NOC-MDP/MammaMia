"""
Script to convert the zarr groups into netCDF files, note, the groups cannot be nested so converting campaign directly is
not supported. E.g. trajectory, reality, of a specific mission can be convertd in this way. As can the different world nested groups.
"""

import xarray as xr
import numpy as np

# Open the Zarr dataset
ds = xr.open_zarr("campaign_1.zarr/mission_1/world/cmems_mod_glo_phy_my_0.083deg_P1D-m")

# Function to fix or remove incompatible fill values
def fix_fill_values(ds):
    for var_name, var in ds.variables.items():
        # Check if _FillValue exists and is incompatible
        if "_FillValue" in var.attrs:
            fill_value = var.attrs["_FillValue"]
            dtype = var.dtype

            # Ensure that the fill value is compatible with the variable's data type
            if np.issubdtype(dtype, np.floating):
                # Set fill value to NaN for floating-point types
                var.attrs["_FillValue"] = np.nan
            elif np.issubdtype(dtype, np.integer):
                # Set fill value to -9999 or some other appropriate value for integer types
                var.attrs["_FillValue"] = -9999
            else:
                # Remove the fill value if incompatible (or handle accordingly)
                del var.attrs["_FillValue"]
        # Remove any invalid NetCDF attributes if necessary
        invalid_attrs = ["spatial_extent","temporal_extent"]
        for attr in invalid_attrs:
            if attr in ds.attrs:
                del ds.attrs[attr]

    return ds

# Apply the fix to the dataset
ds_fixed = fix_fill_values(ds)

# Now save the dataset to NetCDF, ignoring invalid attributes
ds_fixed.to_netcdf("cmems_world_phy.nc")