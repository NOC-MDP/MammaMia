# Copyright 2025 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cartopy.feature as cfeature
import numpy as np
import plotly.graph_objects as go
import xarray as xr
from dash import Dash, Input, Output, callback, dcc, html
from loguru import logger
from shapely.geometry import box

COLOUR_SCALES = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]


def build_sensor_vars(mission: xr.DataTree) -> dict[str, dict[str, any]]:
    """Build nested lookup: {sensor_name: {var_name: DataArray}}"""
    sensor_vars = {}
    for s_key, sensor_ds in mission.payload.items():
        sensor_vars[s_key] = {
            key: payload
            for key, payload in sensor_ds.items()
            if key not in ("latitude", "longitude", "depth", "time")
        }
    return sensor_vars


def get_coords(mission: xr.DataTree, s_key: str):
    sensor_ds = mission.payload[s_key]
    return (
        np.array(sensor_ds["longitude"].values),
        np.array(sensor_ds["latitude"].values),
        np.array(sensor_ds["depth"].values),
    )


def add_map_floor(fig, lon, lat, depth):
    floor_z = np.nanmax(depth)
    lon_pad = (np.nanmax(lon) - np.nanmin(lon)) * 0.2
    lat_pad = (np.nanmax(lat) - np.nanmin(lat)) * 0.2
    extent_box = box(
        np.nanmin(lon) - lon_pad,
        np.nanmin(lat) - lat_pad,
        np.nanmax(lon) + lon_pad,
        np.nanmax(lat) + lat_pad,
    )

    coastlines = cfeature.NaturalEarthFeature("physical", "coastline", "10m")
    for geom in coastlines.geometries():
        clipped = geom.intersection(extent_box)
        if clipped.is_empty:
            continue
        for line in clipped.geoms if hasattr(clipped, "geoms") else [clipped]:
            xs, ys = line.xy
            fig.add_trace(
                go.Scatter3d(
                    x=list(xs),
                    y=list(ys),
                    z=[floor_z] * len(xs),
                    mode="lines",
                    line=dict(color="black", width=2),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )

    land = cfeature.NaturalEarthFeature("physical", "land", "10m")
    for geom in land.geometries():
        clipped = geom.intersection(extent_box)
        if clipped.is_empty:
            continue
        for poly in clipped.geoms if hasattr(clipped, "geoms") else [clipped]:
            xs, ys = poly.exterior.xy
            fig.add_trace(
                go.Scatter3d(
                    x=list(xs),
                    y=list(ys),
                    z=[floor_z] * len(xs),
                    mode="lines",
                    line=dict(color="rgba(180,180,180,0.3)", width=0.5),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    return fig


def add_bathy_contours(fig, lon, lat, depth, contour_interval=50):
    import xarray as xr
    from scipy.ndimage import gaussian_filter

    floor_z = np.nanmax(depth)

    # --- Fetch ETOPO bathymetry via OPeNDAP (requires internet connection) ---
    lon_pad = (np.nanmax(lon) - np.nanmin(lon)) * 0.3
    lat_pad = (np.nanmax(lat) - np.nanmin(lat)) * 0.3
    lon_min, lon_max = np.nanmin(lon) - lon_pad, np.nanmax(lon) + lon_pad
    lat_min, lat_max = np.nanmin(lat) - lat_pad, np.nanmax(lat) + lat_pad

    etopo_url = "https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/30s/30s_bed_elev_netcdf/ETOPO_2022_v1_30s_N90W180_bed.nc"
    ds = xr.open_dataset(etopo_url)
    bathy = ds["z"].sel(
        lon=slice(lon_min, lon_max),
        lat=slice(lat_min, lat_max),
    )

    # Keep only ocean (negative values) and smooth slightly
    bathy_vals = gaussian_filter(bathy.values.astype(float), sigma=1)
    bathy_vals[bathy_vals > 0] = np.nan  # mask land

    bathy_lon = bathy.lon.values
    bathy_lat = bathy.lat.values

    # --- Generate contours using matplotlib (not rendered, just for coords) ---
    import matplotlib

    matplotlib.use("Agg")  # non-interactive backend
    import matplotlib.pyplot as plt

    lon_grid, lat_grid = np.meshgrid(bathy_lon, bathy_lat)

    # Contour levels from surface to max mission depth
    max_depth = int(np.nanmax(np.abs(bathy_vals)))
    levels = np.arange(-max_depth, 0, contour_interval)

    fig_mpl, ax = plt.subplots()
    cs = ax.contour(lon_grid, lat_grid, bathy_vals, levels=levels)
    plt.close(fig_mpl)

    from shapely.geometry import MultiLineString
    from shapely.ops import linemerge

    for level, segs in zip(cs.levels, cs.allsegs):
        if not segs:
            continue

        # Merge all segments at this level into continuous lines
        multi = MultiLineString([seg.tolist() for seg in segs if len(seg) >= 2])
        merged = linemerge(multi)

        lines = merged.geoms if hasattr(merged, "geoms") else [merged]
        for line in lines:
            coords = np.array(line.coords)
            fig.add_trace(
                go.Scatter3d(
                    x=coords[:, 0],
                    y=coords[:, 1],
                    z=[floor_z] * len(coords),
                    mode="lines",
                    line=dict(
                        color="rgba(0,0,128,0.5)",
                        width=1,
                    ),
                    showlegend=False,
                    hoverinfo="skip",
                    name=f"{int(abs(level))}m",
                )
            )

    return fig


def add_bathy_heatmap(fig, lon, lat, depth, downsample=5):
    import xarray as xr
    from scipy.ndimage import gaussian_filter

    floor_z = np.nanmax(depth)

    # --- Fetch ETOPO bathymetry via OPeNDAP ---
    lon_pad = (np.nanmax(lon) - np.nanmin(lon)) * 0.3
    lat_pad = (np.nanmax(lat) - np.nanmin(lat)) * 0.3
    lon_min, lon_max = np.nanmin(lon) - lon_pad, np.nanmax(lon) + lon_pad
    lat_min, lat_max = np.nanmin(lat) - lat_pad, np.nanmax(lat) + lat_pad

    etopo_url = "https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/30s/30s_bed_elev_netcdf/ETOPO_2022_v1_30s_N90W180_bed.nc"
    ds = xr.open_dataset(etopo_url)
    bathy = ds["z"].sel(
        lon=slice(lon_min, lon_max),
        lat=slice(lat_min, lat_max),
    )

    # Smooth and mask land
    bathy_vals = gaussian_filter(bathy.values.astype(float), sigma=1)
    bathy_vals[bathy_vals > 0] = np.nan

    bathy_lon = bathy.lon.values
    bathy_lat = bathy.lat.values

    # --- Downsample to keep the Surface trace lightweight ---
    bathy_vals_ds = bathy_vals[::downsample, ::downsample]
    bathy_lon_ds = bathy_lon[::downsample]
    bathy_lat_ds = bathy_lat[::downsample]

    lon_grid, lat_grid = np.meshgrid(bathy_lon_ds, bathy_lat_ds)

    # z is flat at floor_z; colour encodes actual depth via surfacecolor
    z_flat = np.full_like(bathy_vals_ds, fill_value=floor_z)

    fig.add_trace(
        go.Surface(
            x=lon_grid,
            y=lat_grid,
            z=z_flat,  # keeps the surface on the floor plane
            surfacecolor=bathy_vals_ds,  # actual depth drives the colour
            colorscale="Blues_r",  # deep = dark blue, shallow = light
            cmin=np.nanmin(bathy_vals_ds),
            cmax=0,
            showscale=True,
            colorbar=dict(
                title=dict(
                    text="Depth (m)", side="top"
                ),  # "top" places title above a horizontal bar
                orientation="h",  # horizontal layout
                thickness=15,
                len=0.4,  # fraction of plot width
                x=0.5,  # centred horizontally
                xanchor="center",
                y=-0.05,  # below the plot (negative = outside axes)
                yanchor="top",
            ),
            opacity=0.85,
            showlegend=False,
            hovertemplate=(
                "Lon: %{x:.3f}°<br>"
                "Lat: %{y:.3f}°<br>"
                "Depth: %{surfacecolor:.0f} m"
                "<extra></extra>"
            ),
            name="Bathymetry",
        )
    )

    return fig


def make_figure(lon, lat, depth, color, title: str, colorscale: str) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=lon,
                y=lat,
                z=depth,
                mode="markers",
                marker=dict(
                    size=2,
                    color=color,
                    colorscale=colorscale,
                    cmin=np.nanmin(color),
                    cmax=np.nanmax(color),
                    opacity=0.8,
                    colorbar=dict(thickness=40),
                ),
            )
        ]
    )
    fig.update_scenes(zaxis_autorange="reversed")
    fig.update_layout(
        title=dict(text=title, font=dict(size=24), automargin=True, yref="paper"),
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Depth",
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        uirevision="constant",
    )
    fig = add_map_floor(fig, lon, lat, depth)
    # fig = add_bathy_contours(fig, lon, lat, depth, contour_interval=250)
    # fig = add_bathy_heatmap(fig, lon, lat, depth, downsample=5)
    return fig


def create_dashboard(mission: xr.DataTree, port: int = 8050, debug: bool = True):
    """
    Creates and runs a Dash dashboard with an interactive 3D payload plot.

    Dropdowns:
      - Sensor    → filters which sensor is active
      - Variable  → all variables for the selected sensor
      - Colour Scale → switches the Plotly colorscale
    """
    sensor_vars = build_sensor_vars(mission)

    initial_sensor = next(iter(sensor_vars))
    initial_var = next(iter(sensor_vars[initial_sensor]))

    sensor_options = [{"label": s, "value": s} for s in sensor_vars]

    def variable_options_for(sensor: str):
        return [{"label": v, "value": v} for v in sensor_vars[sensor]]

    colorscale_options = [{"label": cs, "value": cs} for cs in COLOUR_SCALES]

    # ------------------------------------------------------------------ layout
    app = Dash(__name__)
    app.layout = html.Div(
        style={
            "fontFamily": "sans-serif",
            "padding": "16px",
            "backgroundColor": "#f8f9fa",
        },
        children=[
            html.H2(
                f"Mission {mission.attrs['mission_attrs']['name']} Payload Dashboard",
                style={"marginBottom": "4px"},
            ),
            html.Hr(),
            # Controls row
            html.Div(
                style={
                    "display": "flex",
                    "gap": "24px",
                    "alignItems": "flex-end",
                    "marginBottom": "16px",
                },
                children=[
                    html.Div(
                        [
                            html.Label("Sensor", style={"fontWeight": "bold"}),
                            dcc.Dropdown(
                                id="sensor-dropdown",
                                options=sensor_options,
                                value=initial_sensor,
                                clearable=False,
                                style={"minWidth": "180px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Variable", style={"fontWeight": "bold"}),
                            dcc.Dropdown(
                                id="variable-dropdown",
                                options=variable_options_for(initial_sensor),
                                value=initial_var,
                                clearable=False,
                                style={"minWidth": "220px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Colour Scale", style={"fontWeight": "bold"}),
                            dcc.Dropdown(
                                id="colorscale-dropdown",
                                options=colorscale_options,
                                value="Jet",
                                clearable=False,
                                style={"minWidth": "150px"},
                            ),
                        ]
                    ),
                ],
            ),
            # Plot
            dcc.Graph(
                id="payload-plot",
                style={"height": "75vh"},
                config={"scrollZoom": True},
            ),
        ],
    )

    # ----------------------------------------------------------- callbacks

    @app.callback(
        Output("variable-dropdown", "options"),
        Output("variable-dropdown", "value"),
        Input("sensor-dropdown", "value"),
    )
    def update_variable_options(sensor: str):
        """When the sensor changes, repopulate the variable dropdown."""
        opts = variable_options_for(sensor)
        return opts, opts[0]["value"]

    @app.callback(
        Output("payload-plot", "figure"),
        Input("sensor-dropdown", "value"),
        Input("variable-dropdown", "value"),
        Input("colorscale-dropdown", "value"),
    )
    def update_plot(sensor: str, variable: str, colorscale: str):
        if sensor is None or variable is None:
            return go.Figure()

        lon, lat, depth = get_coords(mission, sensor)
        color = np.array(sensor_vars[sensor][variable].values)
        title = f"{sensor}: {variable}"

        fig = make_figure(lon, lat, depth, color, title, colorscale)
        logger.info(
            "Plot updated — sensor=%s variable=%s colorscale=%s",
            sensor,
            variable,
            colorscale,
        )
        return fig

    app.run(debug=debug, port=port, use_reloader=False)


# ---------------------------------------------------------------------------
# Convenience wrapper matching the original function signature
# ---------------------------------------------------------------------------


def start_payload_dashboard(
    mission: xr.DataTree, parameter=None, in_app: bool = False, port: int = 8050
):
    """
    Drop-in replacement for the original plot_payload function.

    When `parameter` is None (default) a full Dash dashboard is launched.
    When `parameter` is supplied a static Plotly figure is returned / shown,
    preserving backwards-compatibility with the original behaviour.
    """
    logger.info("starting payload dashboard...")
    if parameter is None:
        create_dashboard(mission, port=port)
    else:
        color = np.array(mission.payload[parameter][:])
        fig = make_figure(
            lon=mission.payload["longitude"][:],
            lat=mission.payload["latitude"][:],
            depth=mission.payload["depth"][:],
            color=color,
            title=f"Payload: {parameter}",
            colorscale="Jet",
        )
        if not in_app:
            fig.show()
        else:
            return fig


def plot_path(
    mission: xr.DataTree,
    colour_scale: str = "Viridis",
):
    """
    Created an interactive plot of the auv trajectory, with the datetime of the trajectory colour mapped onto it.

    Args:
        colour_scale: (optional) colour scale to use when plotting datetime onto trajectory

    Returns:
        interactive plotly figure that opens in a web browser.

    """
    marker = {
        "size": 2,
        "color": np.array(mission.payload["ctd"].time).tolist(),
        "colorscale": colour_scale,
        "opacity": 0.8,
        "colorbar": {"thickness": 40},
    }

    title = {
        "text": "Glider Trajectory",
        "font": {"size": 30},
        "automargin": True,
        "yref": "paper",
    }

    scene = {
        "xaxis_title": "longitude",
        "yaxis_title": "latitude",
        "zaxis_title": "depth",
    }

    fig = go.Figure(
        data=[
            go.Scatter3d(
                x=mission.payload["ctd"]["longitude"],
                y=mission.payload["ctd"]["latitude"],
                z=mission.payload["ctd"]["depth"],
                mode="markers",
                marker=marker,
            )
        ]
    )
    fig.update_scenes(zaxis_autorange="reversed")
    fig.update_layout(title=title, scene=scene)
    fig.show()
