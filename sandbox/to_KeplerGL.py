import csv

import geojson
import zarr
import numpy as np
from shapely.geometry.geo import mapping

# stride = 180

ds = zarr.open("../RAPID_array_virtual_mooring.zarr/RAD24_01/payload")
lat = ds["LATITUDE"][:]
lon = ds["LONGITUDE"][:]
depth = ds["GLIDER_DEPTH"][:] * -1 # the -1 is to invert the depths so they plot the "right" way round in kepler.gl
time = ds["TIME"][:]
temp = ds["INSITU_TEMPERATURE"][:]
sal = ds["PRACTICAL_SALINITY"][:]
#chlor = ds["CHLOROPHYLL"][:]
time = (time/1e9).astype("datetime64[s]").astype(int)

# # stride arrays (resolution too high for animations)
# lat = lat[::stride]
# lon = lon[::stride]
# depth = depth[::stride]
# time = time[::stride]
# chlor = chlor[::stride]
# heading = heading[::stride]
# temp = temp[::stride]
# sal = sal[::stride]

# mask based on null temps
mask = ~np.isnan(temp)
temp = temp[mask]
sal = sal[mask]
#chlor = chlor[mask]
lat = lat[mask]
lon = lon[mask]
depth = depth[mask]
time = time[mask]

file_name = "RAPID_MOORING2.csv"
with open(file_name, 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)

    # Write the header
    csvwriter.writerow(['Latitude', 'Longitude', 'Depth','Time','Temperature','Salinity'])#,'Chlorophyll'])

    # Generate rows following the pattern
    for i in range(time.__len__()):
        x = lon[i]
        y = lat[i]
        z = depth[i]
        t = time[i]
        t2 = temp[i]
        s = sal[i]
        #c = chlor[i]

        csvwriter.writerow([y,x,z,t,t2,s])#,c])

# from shapely.geometry import Polygon
# import math
#
# def make_arrow(lat, lon, heading_deg, length=0.001):
#     angle = math.radians(heading_deg)
#     dx = length * math.cos(angle)
#     dy = length * math.sin(angle)
#
#     # Arrow triangle (tip, back left, back right)
#     tip = (lon + dx, lat + dy)
#     base_left = (lon - dy * 0.2, lat + dx * 0.2)
#     base_right = (lon + dy * 0.2, lat - dx * 0.2)
#
#     return Polygon([tip, base_left, base_right, tip])
#
#
# features = []
#
# for i in range(time.__len__()):
#     arrow = make_arrow(lat[i], lon[i], heading[i])
#     feature = geojson.Feature(geometry=mapping(arrow), properties={"timestamp": int(time[i]), "latitude": lat[i], "longitude": lon[i]})
#     features.append(feature)
#
# feature_collection = geojson.FeatureCollection(features)
#
# with open("BIO_CARBON_649.geojson", "w") as f:
#     geojson.dump(feature_collection, f, indent=2)
#


# # Make sure all arrays are the same length
# n = min(len(temp), len(lat), len(lon), len(depth), len(time))
# points = [
#     (float(temp[i]), float(lat[i]), float(lon[i]), float(depth[i]), int(time[i]))
#     for i in range(n)
# ]
#
#
# # Build features between consecutive points
# features = []
# for i in range(len(points) - 1):
#     t1, lat1, lon1, depth1, time1 = points[i]
#     t2, lat2, lon2, depth2, time2 = points[i + 1]
#
#     avg_temp = (t1 + t2) / 2
#
#     feature = {
#         "type": "Feature",
#         "properties": {
#             "temperature": avg_temp
#         },
#         "geometry": {
#             "type": "LineString",
#             "coordinates": [
#                 [lon1, lat1, depth1, time1],
#                 [lon2, lat2, depth2, time2]
#             ]
#         }
#     }
#     features.append(feature)
#
# # Final GeoJSON FeatureCollection
# geojson = {
#     "type": "FeatureCollection",
#     "features": features
# }
#
# # Output (as string or save to file)
# with open("RAPID_MOORING.geojson", "w") as f:
#    json.dump(geojson,f, indent=2)