import json
import zarr
import numpy as np

ds = zarr.open("../RAPID_array_virtual_mooring.zarr/RAD24_01/payload")
lat = ds["LATITUDE"][:]
lon = ds["LONGITUDE"][:]
depth = ds["GLIDER_DEPTH"][:] * -1
pitch = ds["GLIDER_PITCH"][:]
time = ds["TIME"][:]
temp = ds["INSITU_TEMPERATURE"]
temp = np.where(np.isnan(temp),8.00,temp)
time = time.astype("datetime64[s]").astype(int)/1e9

# Make sure all arrays are the same length
n = min(len(temp), len(lat), len(lon), len(depth), len(time))
points = [
    (float(temp[i]), float(lat[i]), float(lon[i]), float(depth[i]), int(time[i]))
    for i in range(n)
]


# Build features between consecutive points
features = []
for i in range(len(points) - 1):
    t1, lat1, lon1, depth1, time1 = points[i]
    t2, lat2, lon2, depth2, time2 = points[i + 1]

    avg_temp = (t1 + t2) / 2

    feature = {
        "type": "Feature",
        "properties": {
            "temperature": avg_temp
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [lon1, lat1, depth1, time1],
                [lon2, lat2, depth2, time2]
            ]
        }
    }
    features.append(feature)

# Final GeoJSON FeatureCollection
geojson = {
    "type": "FeatureCollection",
    "features": features
}

# Output (as string or save to file)
with open("RAPID_MOORING.geojson", "w") as f:
    json.dump(geojson,f, indent=2)