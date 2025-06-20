# """
# Script to convert the zarr groups into netCDF files, note, the groups cannot be nested so converting campaign directly is
# not supported. E.g. trajectory, reality, of a specific mission can be convertd in this way. As can the different world nested groups
# """
# from random import random
#
import pandas as pd
import zarr
import numpy as np
import laspy
import matplotlib.pyplot as plt
import pyproj
from netCDF4 import Dataset
from scipy.interpolate import griddata



# Open the Zarr dataset
ds = zarr.open("../BIO-Carbon.zarr/Deployment 650/payload")

# Function to fix or remove incompatible fill values
def fix_fill_values(ds):
    for var in ds.values():
        # Check if _FillValue exists and is incompatible
        if "_FillValue" in var.attrs:
            fill_value = var.attrs["_FillValue"]
            dtype = var.dtype

            # Ensure that the fill value is compatible with the variable's data type
            if np.issubdtype(dtype, np.floating):
                # Set fill value to NaN for floating-point types
                var.attrs["_FillValue"] = np.nan
            elif np.issubdtype(dtype, np.integer):
                # Set fill value to -9999 or some other appropriate value for integer types
                var.attrs["_FillValue"] = -9999
            else:
                # Remove the fill value if incompatible (or handle accordingly)
                del var.attrs["_FillValue"]
        # Remove any invalid NetCDF attributes if necessary
        invalid_attrs = ["spatial_extent","temporal_extent"]
        for attr in invalid_attrs:
            if attr in ds.attrs:
                del ds.attrs[attr]

    return ds
# Apply the fix to the dataset
#ds_fixed = fix_fill_values(ds)

def convert_to_decimal(x):
    """
    Converts a latitiude or longitude in NMEA format to decimale degrees
    """
    sign = np.sign(x)
    x_abs = np.abs(x)
    degrees = np.floor(x_abs / 100.)
    minutes = x_abs - degrees * 100
    decimal_format = degrees + minutes / 60.
    return decimal_format * sign

def temperature_to_rgb(temp):
    """Map temperature data to RGB values using a colormap."""
    # Normalize the temperature values between 0 and 1
    norm_temp = (temp - np.nanmin(temp)) / (np.nanmax(temp) - np.nanmin(temp))

    # Use matplotlib colormap (e.g., 'viridis')
    colormap = plt.get_cmap('jet')
    rgba_colors = colormap(norm_temp)

    # Convert RGBA to 8-bit RGB (0-255)
    rgb_colors = (rgba_colors[:, :3] * 255).astype(np.uint16)
    return rgb_colors[:, 0], rgb_colors[:, 1], rgb_colors[:, 2]

lat = ds["ALATPT01"][:]
lon = ds["ALONPT01"][:]
depth = ds["ADEPPT01"][:]
pitch = ds["PTCHPT01"][:]
time = ds["TIME"][:]

# Convert to DataFrame for convenience
df = pd.DataFrame({'time': time, 'pitch': pitch})

# Apply rolling mean
window_size = 30  # adjust depending on how much smoothing you want
df['pitch_smoothed'] = df['pitch'].rolling(window=window_size, center=True).mean()

pitch = df['pitch_smoothed']
temp = ds["TEMP"][:]
sal = ds["CNDC"][:]
max_temp = 0
max_sal = 0
min_temp = 999
min_sal = 999
for i in range(temp.__len__()):
    if temp[i] > max_temp:
        max_temp = temp[i]
    if temp[i] < min_temp:
        min_temp = temp[i]
    if sal[i] > max_sal:
        max_sal = sal[i]
    if sal[i] < min_sal:
        min_sal = sal[i]

temp[0] = max_temp
sal[0] = max_sal
temp_r,temp_gr,temp_bl = temperature_to_rgb(temp)
sal_r,sal_g,sal_b = temperature_to_rgb(sal)

import csv
file_name = "BIO_CARBON_650.csv"
with open(file_name, 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)

    # Write the header
    csvwriter.writerow(['Row', 'Latitude', 'Longitude', 'Depth','Pitch','Roll','Yaw','Temperature','Red','Green','Blue','Alpha','Salinity','Red2','Green2','Blue2','Alpha2'])

    # Generate rows following the pattern
    for i in range(ds["TIME"].__len__()):
        row_id = f"AUV1-TS{i+1}"

        x = lon[i]
        y = lat[i]
        if np.isnan(depth[i]):
            z = 0
        else:
            z = depth[i]
        if np.isnan(pitch[i]):
            p = 0
        else:
            p = pitch[i]#np.rad2deg(pitch[i])

        yaw = 0
        roll = 0
        if i == 0:
            t = max_temp
        elif i == 1:
            t = min_temp
        elif np.isnan(temp[i]):
            t = min_temp
        else:
            t = temp[i]
        if i == 0:
            s = max_sal
        elif i == 1:
            s = min_sal
        elif np.isnan(sal[i]):
            s = min_sal
        else:
            s = sal[i]
        re1 = temp_r[i]
        gr1 = temp_gr[i]
        bl1 = temp_bl[i]
        re2 = sal_r[i]
        gr2 = sal_g[i]
        bl2 = sal_b[i]
        alp = 1.0
        csvwriter.writerow([row_id, y,x,z,p,roll,yaw,t,re1,gr1,bl1,alp,s,re2,gr2,bl2,alp])

# X,Y,Z = np.meshgrid(lon.values,lat.values,depth.values)
# project = pyproj.Transformer.from_crs("EPSG:4326","EPSG:3857", always_xy=True)
# X_m, Y_m = project.transform(X, Y)
# temp = ds_fixed["thetao"][0,:,:,:]

# # # # # Sample data
# num_particles = ds_fixed["datetimes"].shape[0]  # Number of particles
# # # #
# # # # # Static position data: shape (P, axis) where axis=3 for (x, y, z) components
# lat = []
# lon = []
# # # #
# for i in range(num_particles):
#       lat.append(convert_to_decimal(ds_fixed["latitudes"][i].values))
#       lon.append(convert_to_decimal(ds_fixed["longitudes"][i].values))

# depth = ds_fixed["depths"]
# #X,Y,Z = np.meshgrid(lon.values,lat.values,depth.values)
# # project = pyproj.Transformer.from_crs("EPSG:4326","EPSG:3857", always_xy=True)
# # X_m, Y_m = project.transform(X, Y)
# temp = ds_fixed["temperature"]


#
# header = laspy.LasHeader(point_format=3,version="1.4")
# las = laspy.LasData(header)
# crs = pyproj.CRS.from_epsg(3857)
# las.header.add_crs(crs)
#
# x = X_m.flatten()
# y = Y_m.flatten()
# z = Z.flatten()
# temp = temp.values.flatten()
# #red, green, blue = temperature_to_rgb(temp)
#
#
# # # Step 1: Calculate temperature gradient with respect to depth
# # sorted_indices = np.argsort(z)
# # sorted_z = z[sorted_indices]
# # sorted_temps = temp[sorted_indices]
# #
# # # Calculate the gradient along the depth axis
# # depth_diff = np.diff(sorted_z)
# # temp_diff = np.diff(sorted_temps)
# # gradient = np.abs(temp_diff / depth_diff)
# # gradient = np.append(gradient, 0)
# #
# # # Normalize the gradient to use as intensity (0-65535)
# # intensity = (gradient / gradient.max() * 65535).astype(np.uint16)
# # intensity_unsorted = intensity[np.argsort(sorted_indices)]
#
# num_interp_points_x = lat.__len__() * 50  # Increase for denser interpolation
# num_interp_points_y = lon.__len__() * 50
# num_interp_points_z = depth.__len__()
# # Generate new points for interpolation between lat/lon coordinates
# xi = np.linspace(x.min(), x.max(), num_interp_points_x)
# yi = np.linspace(y.min(), y.max(), num_interp_points_y)
# zi = np.linspace(z.min(), z.max(), num_interp_points_z)
# xi, yi, zi = np.meshgrid(xi, yi, zi)
#
# # Flatten the grid arrays
# interp_coords = np.vstack([xi.ravel(), yi.ravel(), zi.ravel()]).T
#
# # Interpolate temperatures onto the new grid
# interpolated_temps = griddata(
#     (x, y, z), temp, interp_coords, method='linear', fill_value=np.nan
# )
#
# # # Interpolate intensity values onto the new grid
# # interpolated_intensity = griddata(
# #     (x, y, z), intensity_unsorted, interp_coords, method='linear', fill_value=0
# # )
#
# # Filter out NaN values after interpolation
# valid_mask = ~np.isnan(interpolated_temps)
# interp_coords = interp_coords[valid_mask]
# interpolated_temps = interpolated_temps[valid_mask]
# #interpolated_intensity = interpolated_intensity[valid_mask]
#
# # Step 3: Create a new LAS file with the interpolated data
# las.x = interp_coords[:, 0].astype(np.int32)
# las.y = interp_coords[:, 1].astype(np.int32)
# las.z = interp_coords[:, 2].astype(np.int32)
#
# red, green, blue = temperature_to_rgb(interpolated_temps)
# # Map the interpolated temperatures to RGB (you can adjust this mapping)
# las.red = red
# las.green = green
# las.blue = blue
#
# # Set the interpolated intensity values
# #las.intensity = interpolated_intensity.astype(np.uint16)
#
# # Save the new LAS file with interpolated points
# las.write("mworld_1_interp.las")

# las.x = lon[11:]
# las.y = lat[11:]
# las.z = depth[11:].values
# las.temperature = temp[11:].values
# las.write("reality_1.las")

# lats = []
# lons = []
# # # #
# for i in range(ds_fixed["latitude"].shape[0]):
#       lats.append(convert_to_decimal(ds_fixed["latitude"][i].values))
# for i in range(ds_fixed["longitude"].shape[0]):
#       lons.append(convert_to_decimal(ds_fixed["longitude"][i].values))
#
# import numpy as np
# from pygltflib import *
# from matplotlib import cm
#
#
# def temperature_to_rgb(temp, temp_min, temp_max):
#     """ Map temperature to RGB color based on a linear scale. """
#     norm_temp = (temp - temp_min) / (temp_max - temp_min)
#     colourmap = cm.get_cmap('jet')
#     return colourmap(norm_temp)[:3]  # Using the 'viridis' colormap for colors
#
#
# if __name__ == "__main__":
#     output_path = "cmems.glb"
#
#     # Example gridded data (lat, lon, depth, temperature)
#     latitudes = lats # 5 latitudes from 10 to 20
#     longitudes = lons  # 5 longitudes from 100 to 110
#     depths = ds_fixed["depth"].values  # Random depths for each grid point
#     temperatures = ds_fixed["thetao"][0,:,:,:].values # Random temperatures for each grid point
#
#     # Define temperature range for color mapping
#     temp_min = np.nanmin(temperatures)
#     temp_max = np.nanmax(temperatures)
#
#     # Generate vertices (lat, lon, depth as 3D coordinates)
#     vertices_lst = []
#     for lat in latitudes:
#         for lon in longitudes:
#             for depth in depths:
#                 vertices_lst.append([lat, lon, depth])
#
#     # Convert temperature to RGB colors for each vertex
#     vertices_colors_lst = []
#     for temp in temperatures.flat:
#         color = temperature_to_rgb(temp, temp_min, temp_max)
#         vertices_colors_lst.append(color)
#
#     # Generate faces for the gridded data (triangulate each grid cell)
#     faces_lst = []
#     for i in range(len(latitudes) - 1):
#         for j in range(len(longitudes) - 1):
#             # Indices of the four vertices in the grid cell
#             v0 = i * len(longitudes) + j
#             v1 = v0 + 1
#             v2 = v0 + len(longitudes)
#             v3 = v2 + 1
#
#             # Two triangles for each square (quad)
#             faces_lst.append([v0, v1, v2])  # Triangle 1
#             faces_lst.append([v1, v3, v2])  # Triangle 2
#
#     # Convert color list to NumPy array
#     vertices_colors_nparray = np.array([np.array(xi) for xi in vertices_colors_lst])
#
#     # Initialize GLTF2 structure
#     gltf = GLTF2()
#     gltf.asset = Asset()
#     gltf.scenes = [Scene()]
#     gltf.nodes = [Node()]  # Mesh node
#     gltf.meshes = [Mesh()]
#     gltf.accessors = [Accessor() for _ in range(3)]  # faces, vertices, vertex_colors
#     gltf.materials = [Material()]
#     gltf.bufferViews = [BufferView() for _ in range(3)]
#     gltf.buffers = [Buffer()]
#
#     # Scene setup
#     gltf.scene = 0
#
#     # Store faces (indices)
#     indices_chunk = b""
#     for f in faces_lst:
#         indices_chunk += struct.pack("<III", *f)
#
#     gltf.bufferViews[0].buffer = 0
#     gltf.bufferViews[0].byteOffset = 0
#     gltf.bufferViews[0].byteLength = len(indices_chunk)
#     gltf.bufferViews[0].target = ELEMENT_ARRAY_BUFFER
#     gltf.accessors[0].bufferView = 0
#     gltf.accessors[0].byteOffset = 0
#     gltf.accessors[0].componentType = UNSIGNED_INT
#     gltf.accessors[0].normalized = False
#     gltf.accessors[0].count = len(faces_lst) * 3
#     gltf.accessors[0].type = "SCALAR"
#
#     # Store vertices
#     vertices_chunk = b""
#     for v in vertices_lst:
#         vertices_chunk += struct.pack("<fff", *v)
#
#     gltf.bufferViews[1].buffer = 0
#     gltf.bufferViews[1].byteOffset = gltf.bufferViews[0].byteLength
#     gltf.bufferViews[1].byteLength = len(vertices_chunk)
#     gltf.bufferViews[1].target = ARRAY_BUFFER
#     gltf.accessors[1].bufferView = 1
#     gltf.accessors[1].byteOffset = 0
#     gltf.accessors[1].componentType = FLOAT
#     gltf.accessors[1].normalized = False
#     gltf.accessors[1].count = len(vertices_lst)
#     gltf.accessors[1].type = "VEC3"
#     gltf.accessors[1].max = list(np.max(np.array(vertices_lst).T, axis=1))  # Max values for normalization
#     gltf.accessors[1].min = list(np.min(np.array(vertices_lst).T, axis=1))  # Min values for normalization
#
#     # Store vertex colors
#     vcolor_chunk = b""
#     for vc in vertices_colors_nparray:
#         vcolor_chunk += struct.pack("<fff", *vc)
#
#     gltf.bufferViews[2].buffer = 0
#     gltf.bufferViews[2].byteOffset = gltf.bufferViews[1].byteOffset + gltf.bufferViews[1].byteLength
#     gltf.bufferViews[2].byteLength = len(vcolor_chunk)
#     gltf.bufferViews[2].target = ARRAY_BUFFER
#     gltf.accessors[2].bufferView = 2
#     gltf.accessors[2].byteOffset = 0
#     gltf.accessors[2].componentType = FLOAT
#     gltf.accessors[2].normalized = False
#     gltf.accessors[2].count = len(vertices_colors_nparray)
#     gltf.accessors[2].type = "VEC3"
#
#     # Store buffer data
#     gltf.identify_uri = BufferFormat.BINARYBLOB
#     gltf._glb_data = indices_chunk + vertices_chunk + vcolor_chunk
#     gltf.buffers[0].byteLength = gltf.bufferViews[2].byteOffset + gltf.bufferViews[2].byteLength
#
#     # Mesh setup
#     gltf.meshes[0].primitives = [
#         Primitive(
#             attributes=Attributes(
#                 POSITION=1,
#                 COLOR_0=2,
#             ),
#             indices=0,
#             material=0
#         )
#     ]
#     gltf.meshes[0].name = "TemperatureMesh"
#
#     # Assemble nodes
#     gltf.nodes[0].mesh = 0
#     gltf.nodes[0].name = "Mesh"
#
#     gltf.scenes[0].nodes = [0]
#
#     # Export to .glb file
#     gltf.save_binary(output_path)

# # ds_fixed.to_netcdf("gl_reality.nc")
#
# # ds_fixed.to_netcdf("gl_reality.nc")
#
# # # Generate example particles for next timestep
# # def StepSimulation() -> None:
# #     global pos, vel
# #     G = 3000
# #     r = np.sqrt(np.sum(pos**2, axis=-1))
# #     r = np.clip(r, 10, 100**2)
# #     d = -pos/r[:,None]
# #     vel += d*(G/r**2)[:,None]
# #     pos += vel * 0.1
# #     # filt = np.column_stack((pos,vel))[np.all((pos>-100) & (pos<100), axis=1)]
# #     # pos = filt[:, 0:dim]
# #     # vel = filt[:, dim:dim*2]
# #
# # # Wraps an array in an additional dimension
# # # This is required for data time varying data that is only spacial
# # # as is this case in this demo
# def AddTimeDim(data: np.ndarray) -> np.ndarray:
#     return np.expand_dims(data, axis=0)
#

#
#
# def haversine_distance_from_reference(lat, lon, ref_lat=90, ref_lon=-180):
#     """
#     Calculate the approximate distance in meters from a specified reference
#     latitude and longitude using the Haversine formula.
#
#     Parameters:
#     - lat: Latitude in decimal degrees (-90 to 90)
#     - lon: Longitude in decimal degrees (-180 to 180)
#     - ref_lat: Reference latitude in decimal degrees (default is -90 for the equator)
#     - ref_lon: Reference longitude in decimal degrees (default is -180 for prime meridian)
#
#     Returns:
#     - Distance in meters from the specified reference point
#     """
#     # Radius of Earth in meters
#     R = 6371000
#
#     # Convert all lat/lon to radians
#     lat, lon, ref_lat, ref_lon = map(np.radians, [lat, lon, ref_lat, ref_lon])
#
#     # Calculate differences
#     dlat = lat - ref_lat
#     dlon = lon - ref_lon
#
#     # Haversine formula
#     a = np.sin(dlat / 2) ** 2 + np.cos(ref_lat) * np.cos(lat) * np.sin(dlon / 2) ** 2
#     c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
#
#     # Distance in meters
#     distance = R * c
#     return distance
#
# def convert_to_vapor_coords(lat:float,lon:float,NMEA=False):
#     if NMEA:
#         lat_decimal = convert_to_decimal(lat)
#         lon_decimal = convert_to_decimal(lon)
#     else:
#         lat_decimal = lat
#         lon_decimal = lon
#     lat_metres = haversine_distance_from_reference(lat=lat_decimal, lon=-180)
#     lon_metres = haversine_distance_from_reference(lat=90, lon=lon_decimal)
#     return lon_metres, lat_metres


# import netCDF4 as nc
# import numpy as np
#
# import netCDF4 as nc
# # import numpy as np
# #
# # # # Sample data
# num_particles = ds_fixed["datetimes"].shape[0]  # Number of particles
# # #
# # # # Static position data: shape (P, axis) where axis=3 for (x, y, z) components
# positions = []
# project = pyproj.Transformer.from_crs("EPSG:4326","EPSG:3857", always_xy=True)
# # #
# for i in range(num_particles):
#      lat = convert_to_decimal(ds_fixed["latitudes"][i].values)
#      lon = convert_to_decimal(ds_fixed["longitudes"][i].values)
#      positions.append([lon_m,lat_m,ds_fixed["depths"][i]])
#      lon_m,lat_m = project.transform(lon,lat)
# # #
# position_data = np.array(positions)
# # # # Speed data: shape (P,)
# temp_data = ds_fixed["temperature"]
# # #
# # # # Create a new NetCDF file
# with nc.Dataset('particles_dcp_static.nc', 'w', format='NETCDF4') as dataset:
#      # Global attributes
#      dataset.Conventions = "CF-1.8"  # Specify CF compliance
#      dataset.title = "Non-time-varying Particle Data"
#      dataset.institution = "Example Institution"
#      dataset.source = "Synthetic data for demonstration"
#      # Define dimensions
#      dataset.createDimension('P', num_particles)
#      dataset.createDimension("axis", 3)
#      # Define variables
#      position_var = dataset.createVariable('Position', 'f4', ('P',"axis"),zlib=True)
#      position_var.units = 'meter'
#      temp_var = dataset.createVariable('temperature', 'f4', ('P',),zlib=True)#
#      temp_var.units = 'Celsius'
# #
# #     # Assign data to variables
#      position_var[:] = position_data
#      temp_var[:] = temp_data
#
# print("Non-time-varying DCP NetCDF file created successfully.")
#
# import rioxarray
# from rasterio.crs import CRS
# # # Step 1: Load the GEBCO bathymetry NetCDF file
# file_path = "../glidersim/gebco_2024_n73.3887_s48.6035_w-61.875_e-28.125.nc"
# xds = rioxarray.open_rasterio(file_path)
# # Ensure the dataset is in a spatial format by setting the CRS if not already set
# if not xds.rio.crs:
#     xds = xds.rio.write_crs("EPSG:4326", inplace=True)
# xds_3857 = xds.rio.reproject("EPSG:3857")
# xds_3857.to_netcdf("epsg3857.nc")
# print("reprojection successful")
#
# # Step 2: Define the projection (e.g., UTM or any projection in meters)
# # Here, we’ll use EPSG:3857, commonly used for Web Mercator in meters
# project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
#
# # Step 3: Convert the latitude and longitude to meters
# lon = ds["lon"].values  # Adjust depending on your NetCDF’s variable names
# lat = ds["lat"].values
# # Step 1: Create a 2D meshgrid from the 1D lat and lon arrays
# lon_2d, lat_2d = np.meshgrid(lon, lat)
#
# lon_m_2d, lat_m_2d = project.transform(lon_2d, lat_2d)
#
# lon_m_1d = lon_m_2d[0,:]
# lat_m_1d = lat_m_2d[:,0]
# # Step 4: Replace coordinates with the new meter-based values
# # If your dataset is gridded, make sure to handle the conversion correctly for both axes.
#
# with nc.Dataset("modified_gebco_file.nc", 'w', format='NETCDF4') as dataset:
#
#     dataset.createDimension('lat', len(lat_m_1d))
#     dataset.createDimension('lon', len(lon_m_1d))
#     elev = dataset.createVariable('elevation', 'int16', ('lat','lon'))
#     lat_var = dataset.createVariable('lat', 'float32', ('lat',))
#     lon_var = dataset.createVariable('lon', 'float32', ('lon',))
#     lat_var[:] = lat_m_1d
#     lon_var[:] = lon_m_1d
#     elev[:] = ds["elevation"].values
#
#
# print("GEBCO bathy transformed successfully")

# # Sample data setup (replace with actual data arrays)
# num_points = 100
# times = np.linspace(0, 10, num_points)  # e.g., time in hours since a start date
# lats = np.random.uniform(-90, 90, num_points)  # latitude in degrees
# lons = np.random.uniform(-180, 180, num_points)  # longitude in degrees
# depths = np.random.uniform(0, 5000, num_points)  # depth in meters
# temperature = np.random.uniform(-2, 30, num_points)  # temperature in Celsius
#
# # Create a new NetCDF file
# with nc.Dataset('trajectory_data.nc', 'w', format='NETCDF4') as dataset:
#     # Create the "trajectory" dimension
#     dataset.createDimension('time', None)
#
#     # Create variables for each component of the trajectory data
#     times_var = dataset.createVariable('time', 'f4', ('time',))
#     lats_var = dataset.createVariable('lat', 'f4', ('time',))
#     lons_var = dataset.createVariable('lon', 'f4', ('time',))
#     depths_var = dataset.createVariable('depth', 'f4', ('time',))
#     temp_var = dataset.createVariable('temperature', 'f4', ('time',))
#
#     # Assign attributes to help with interpretation
#     times_var.units = 'hours since 2000-01-01 00:00:00.0'
#     times_var.calendar = 'gregorian'
#     lats_var.units = 'degrees_north'
#     lons_var.units = 'degrees_east'
#     depths_var.units = 'meters'
#     temp_var.units = 'Celsius'
#
#     # Write data to variables
#     times_var[:] = times
#     lats_var[:] = lats
#     lons_var[:] = lons
#     depths_var[:] = depths
#     temp_var[:] = temperature
#
# print("Trajectory NetCDF file created successfully.")

# N = 2
# dim = 3
# np.random.seed(0)
# #pos = np.random.random_sample((N,dim))*200-100
# vel = np.random.random_sample((N,dim))*20-1
# simulation_len = ds_fixed["datetimes"].shape[0]
# dataset = Dataset(f"particles.nc", "w", format="NETCDF4")
# dataset.createDimension("time", ds_fixed["datetimes"].shape[0])
# dataset.createDimension("latitudes", ds_fixed["datetimes"].shape[0])
# dataset.createDimension("longitudes",  ds_fixed["datetimes"].shape[0])
# dataset.createDimension("depths",ds_fixed["datetimes"].shape[0])
# dataset.createDimension("axis",3)
#
# T = dataset.createVariable("time", "f8", ("time",))
# # T.units = "seconds"
# T[:] = ds_fixed["datetimes"]
#
# L = dataset.createVariable("lat", "f8", ("latitudes",))
# L2 = dataset.createVariable("lon", "f8", ("longitudes",))
# D = dataset.createVariable("depths", "f8", ("depths",))
#
# TEMP = dataset.createVariable("temperature", "f8", ("time","axis"))
# temps = np.zeros(shape=ds_fixed["datetimes"].shape[0])
# lats = np.zeros(shape=ds_fixed["datetimes"].shape[0])
# lons = np.zeros(shape=ds_fixed["datetimes"].shape[0])
# depths = np.zeros(shape=ds_fixed["datetimes"].shape[0])
# for i in range(ds_fixed["datetimes"].shape[0]):
#     lats[i] = convert_to_decimal(ds_fixed["latitudes"][i].values)
#     lons[i] = convert_to_decimal(ds_fixed["longitudes"][i].values)
#     depths[i] = ds_fixed["depths"][i].values
#     temps[i] = ds_fixed["temperature"][i].values
#
# L[:] = lats
# L2[:] = lons
# TEMP[:] = np.array([temps,lats,lons,depths])
#
# dataset.close()

# particleCount: int = N
# dataset.createDimension("P", particleCount)  # The P dimension represents the number of particles at this timestep
# dataset.createDimension("T", None)  # Time dimension
# dataset.createDimension("axis", 3)  # Utility dimension for packing 3 components for 3D particles into a single variable
#
# # Time coordinate

# # ts = []
# positions = np.zeros(shape=(simulation_len,N,3))
# speeds = np.zeros(shape=(simulation_len,N,3))
# # vel_x = np.zeros(shape=(simulation_len,N,3))
# # vel_y = np.zeros(shape=(simulation_len,N,3))
# # vel_z = np.zeros(shape=(simulation_len,N,3))
# for i in range(simulation_len):
#     # ts.append(i+1)
#     pos_lat = convert_to_decimal(ds_fixed["latitudes"][i].values)
#     pos_lng = convert_to_decimal(ds_fixed["longitudes"][i].values)
#     pos_depth = ds_fixed["depths"][i].values
#     pos = np.array([pos_lng, pos_lat, pos_depth])
#     positions[i,:,:] = AddTimeDim(np.array([pos,pos*0.1]))
#     speeds[i,:,:] = AddTimeDim(np.sqrt(np.sum(10*random() ** 2)))
#     # vel_x[i,:,:] = AddTimeDim(vel)
#     # vel_y[i,:,:] = AddTimeDim(vel)
#     # vel_z[i,:,:] = AddTimeDim(vel)
#     # StepSimulation()
#
# # T[:] = np.array(ts)
#
# # 3D vars can be packed in a single variable by adding the axis dimension
# Position = dataset.createVariable("Position", "f4", ("T", "P", "axis"), zlib=True)
# Position[:] = positions
#
# Speed = dataset.createVariable("speed", "f4", ("T", "P", "axis"), zlib=True)
# Speed[:] = speeds
# # VelX = dataset.createVariable("vel_x", "f4", ("T", "P", "axis"), zlib=True)
# # VelX[:] = vel_x
# # VelY = dataset.createVariable("vel_y", "f4", ("T", "P", "axis"), zlib=True)
# # VelY[:] = vel_y
# # VelZ = dataset.createVariable("vel_z", "f4", ("T", "P", "axis"), zlib=True)
# # VelZ[:] = vel_z
# #
#
# dataset.close()



#
# def WriteTimestep(ts: float, positionData: np.ndarray, **kwargs: np.ndarray) -> None:
#     dataset = Dataset(f"particles_{ts:03}.nc", "w", format="NETCDF4")
#
#     particleCount:int = positionData.shape[0]
#     dataset.createDimension("P", particleCount) # The P dimension represents the number of particles at this timestep
#     dataset.createDimension("T", None) # Time dimension
#     dataset.createDimension("axis", 3) # Utility dimension for packing 3 components for 3D particles into a single variable
#
#     # Time coordinate
#     T = dataset.createVariable("T", "f8", ("T",))
#     T.units = "seconds"
#     T[:] = np.array([ts])
#
#     # 3D vars can be packed in a single variable by adding the axis dimension
#     Position = dataset.createVariable("Position", "f4", ("T", "P", "axis"), zlib=True)
#     # positionData is 2D (numParticles * axis) whereas Position is 3D (time * numParticles * axis)
#     Position[:] = AddTimeDim(positionData)
#     # Alternatively, you could do the following:
#     # Position_x = dataset.createVariable("Position_x", "f4", ("T", "P"), zlib=True)
#     # Position_x[:] = AddTimeDim(positionData_x:1d array)
#     # and so on for the other 2 axes
#
#     # Save all remaining particle properties passed in to nc file
#     for name, data in kwargs.items():
#         var = dataset.createVariable(name, "f4", ("T", "P", "axis")[0:data.ndim + 1], zlib=True)
#         var[:] = AddTimeDim(data)
#
#     dataset.close()
#
#
# for ts in range(200):
#     # Compute magnitude of velocity for each particle
#     speed = np.sqrt(np.sum(vel**2, axis=-1))
#     # Since 3-component properties such as velocity are common for 3D particles,
#     # DCP allows packing them as a 2D array of size N_particles by 3
#     # vel is an array of size Nx3 and speed is an array of size N
#     WriteTimestep(ts, pos, vel=vel, speed=speed)
#     # The following would also work
#     # WriteTimestep(ts, pos, vel_x=vel[:,0], vel_y=vel[:,1], vel_z=vel[:,2], speed=speed)
#     StepSimulation()
