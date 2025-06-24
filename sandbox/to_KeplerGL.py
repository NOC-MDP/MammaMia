import csv
import zarr
import numpy as np

ds = zarr.open("../BIO-Carbon.zarr/Deployment_649/payload")
lat = ds["ALATPT01"][:]
lon = ds["ALONPT01"][:]
depth = ds["ADEPPT01"][:] * -1 # the -1 is to invert the depths so they plot the "right" way round in kepler.gl
time = ds["TIME"][:]
temp = ds["INSITU_TEMPERATURE"][:]
sal = ds["PRACTICAL_SALINITY"][:]
chlor = ds["CHLOROPHYLL"][:]
time = (time/1e9).astype("datetime64[s]").astype(int)

# mask based on null temps
mask = ~np.isnan(temp)
temp = temp[mask]
sal = sal[mask]
chlor = chlor[mask]
lat = lat[mask]
lon = lon[mask]
depth = depth[mask]
time = time[mask]

file_name = "BIO_CARBON_649.csv"
with open(file_name, 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)

    # Write the header
    csvwriter.writerow(['Latitude', 'Longitude', 'Depth','Time','Temperature','Salinity','Chlorophyll'])

    # Generate rows following the pattern
    for i in range(time.__len__()):
        x = lon[i]
        y = lat[i]
        z = depth[i]
        t = time[i]
        t2 = temp[i]
        s = sal[i]
        c = chlor[i]

        csvwriter.writerow([y,x,z,t,t2,s,c])



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