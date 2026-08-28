import xarray as xr

from mamma_mia import start_payload_dashboard

campaign = xr.open_datatree("BIOCARBON_2024.zarr")

# TODO this should not be needed
missions = list(campaign.children.values())

start_payload_dashboard(missions=missions)
