import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib import cm  # Colormap

# Generate example AUV track data (Replace this with your actual data)
np.random.seed(42)
time_steps = 100
auv_track = {
    'longitude': np.linspace(-122.5, -122.0, time_steps),
    'latitude': np.linspace(36.5, 37.0, time_steps),
    'depth': -np.cumsum(np.random.randn(time_steps)) - 195  # depth increasing over time
}

track_data = pd.DataFrame(auv_track)
temperature = np.linspace(2, 10, time_steps) + np.random.randn(time_steps)
# Generate example bathymetry data (Replace this with your actual bathymetry data)
lon = np.linspace(-123, -121, 50)
lat = np.linspace(36, 38, 50)
lon_grid, lat_grid = np.meshgrid(lon, lat)
bathymetry = -200 + 20 * np.sin(lon_grid) * np.cos(lat_grid)  # Synthetic bathymetry

# Create a 3D plot
fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111, projection='3d')

# Plot the bathymetry
ax.plot_surface(lon_grid, lat_grid, bathymetry, cmap='viridis', alpha=0.6)

# Initialize the AUV track plot
lines = [ax.plot([], [], [], color='r', linewidth=2)[0] for _ in range(time_steps - 1)]

# Set labels
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_zlabel('Depth')
ax.set_title('AUV Track with Bathymetry (Colored by Temperature)')
ax.set_xlim(np.min(lon_grid), np.max(lon_grid))
ax.set_ylim(np.min(lat_grid), np.max(lat_grid))
ax.set_zlim(np.min(bathymetry), np.max(bathymetry))

# Normalize the temperature data for colormap
norm = plt.Normalize(np.min(temperature), np.max(temperature))
cmap = cm.ScalarMappable(norm=norm, cmap='coolwarm')  # Choose a colormap, e.g., 'coolwarm'

# Add a colorbar to serve as the legend for temperature
cbar = fig.colorbar(cmap, ax=ax, shrink=0.5, aspect=10)
cbar.set_label('Temperature (°C)', rotation=270, labelpad=15)

# Animation update function
def update(num, track_data, temperature, lines):
    for i in range(num):
        # Set line data and color based on temperature
        lines[i].set_data(track_data['longitude'][i:i+2], track_data['latitude'][i:i+2])
        lines[i].set_3d_properties(track_data['depth'][i:i+2])
        lines[i].set_color(cmap.to_rgba(temperature[i]))
    return lines

# Create the animation
ani = FuncAnimation(fig, update, frames=time_steps, fargs=(track_data, temperature, lines), interval=100, blit=False)

# Save the animation as an MP4 file using FFMpegWriter
ani.save('auv_track_bathymetry_colored.mp4', writer='ffmpeg')

# Display the plot
plt.show()