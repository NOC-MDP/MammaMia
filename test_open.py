import xarray as xr

from mamma_mia.plot_xr import plot_payload

campaign = xr.open_datatree("test.zarr")

plot_payload(mission=campaign["mission_0"])
