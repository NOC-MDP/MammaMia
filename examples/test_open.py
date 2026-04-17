import xarray as xr

from mamma_mia import start_payload_dashboard

campaign = xr.open_datatree("RAPID.zarr")
start_payload_dashboard(mission=campaign["Example Glider RAPID"])
