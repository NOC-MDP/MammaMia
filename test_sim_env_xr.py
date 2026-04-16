from mamma_mia.get_data_xr import get_extent
from mamma_mia.interpolator_xr import create_interpolator, interpolate

stores = get_extent(spec_file="rapid_vm_sim_spec.toml")

interpolators = create_interpolator(stores=stores)

point = {
    "latitude": 26.834,
    "longitude": -15.142,
    "depth": 25.0,
    "time": "2023-03-03T00:00:00",
}

interp_data = interpolate(interpolators=interpolators, point=point)
print(interp_data)
