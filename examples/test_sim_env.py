from mamma_mia import create_interpolator, get_extent, interpolate

stores = get_extent(spec_file="spec_files/rapid_vm_sim_spec.toml")

interpolators = create_interpolator(stores=stores, mission=None)

coords = {
    "latitude": [26.834],
    "longitude": [-15.142],
    "depth": [25.0],
    "time": ["2023-03-03T00:00:00"],
}

interp_data = interpolate(interpolators=interpolators, coords=coords)
print(interp_data)
