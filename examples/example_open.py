import xarray as xr

from mamma_mia import start_payload_dashboard

campaign = xr.open_datatree("BIOCARBON_2024.zarr")
start_payload_dashboard(missions=campaign["cabot_645"])
