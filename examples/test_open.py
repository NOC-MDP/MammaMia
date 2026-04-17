import xarray as xr

from mamma_mia import start_payload_dashboard

campaign = xr.open_zarr(store="ALR_6_mission.zarr/payload")
print(campaign)
