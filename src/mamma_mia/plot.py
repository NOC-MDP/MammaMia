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
from dash import Dash, Input, Output, dcc, html
from loguru import logger
from shapely.geometry import box

COLOUR_SCALES = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

# Distinct colours for multi-mission path traces
_MISSION_COLOURS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
]

# Sentinel value used in the Mission dropdown for "show all missions together"
_ALL = "__all__"


def _normalise_missions(
    missions: "xr.DataTree | list[xr.DataTree]",
) -> list[xr.DataTree]:
    """Always return a list, whether one or many missions were passed."""
    if isinstance(missions, xr.DataTree):
        return [missions]
    return list(missions)


# ---------------------------------------------------------------------------
# Sensor / variable helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Map floor / bathymetry helpers  (unchanged)
# ---------------------------------------------------------------------------


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

    lon_pad = (np.nanmax(lon) - np.nanmin(lon)) * 0.3
    lat_pad = (np.nanmax(lat) - np.nanmin(lat)) * 0.3
    lon_min, lon_max = np.nanmin(lon) - lon_pad, np.nanmax(lon) + lon_pad
    lat_min, lat_max = np.nanmin(lat) - lat_pad, np.nanmax(lat) + lat_pad

    etopo_url = "https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/30s/30s_bed_elev_netcdf/ETOPO_2022_v1_30s_N90W180_bed.nc"
    ds = xr.open_dataset(etopo_url)
    bathy = ds["z"].sel(lon=slice(lon_min, lon_max), lat=slice(lat_min, lat_max))

    bathy_vals = gaussian_filter(bathy.values.astype(float), sigma=1)
    bathy_vals[bathy_vals > 0] = np.nan

    bathy_lon = bathy.lon.values
    bathy_lat = bathy.lat.values

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lon_grid, lat_grid = np.meshgrid(bathy_lon, bathy_lat)
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
                    line=dict(color="rgba(0,0,128,0.5)", width=1),
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

    lon_pad = (np.nanmax(lon) - np.nanmin(lon)) * 0.3
    lat_pad = (np.nanmax(lat) - np.nanmin(lat)) * 0.3
    lon_min, lon_max = np.nanmin(lon) - lon_pad, np.nanmax(lon) + lon_pad
    lat_min, lat_max = np.nanmin(lat) - lat_pad, np.nanmax(lat) + lat_pad

    etopo_url = "https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/30s/30s_bed_elev_netcdf/ETOPO_2022_v1_30s_N90W180_bed.nc"
    ds = xr.open_dataset(etopo_url)
    bathy = ds["z"].sel(lon=slice(lon_min, lon_max), lat=slice(lat_min, lat_max))

    bathy_vals = gaussian_filter(bathy.values.astype(float), sigma=1)
    bathy_vals[bathy_vals > 0] = np.nan

    bathy_lon = bathy.lon.values
    bathy_lat = bathy.lat.values

    bathy_vals_ds = bathy_vals[::downsample, ::downsample]
    bathy_lon_ds = bathy_lon[::downsample]
    bathy_lat_ds = bathy_lat[::downsample]

    lon_grid, lat_grid = np.meshgrid(bathy_lon_ds, bathy_lat_ds)
    z_flat = np.full_like(bathy_vals_ds, fill_value=floor_z)

    fig.add_trace(
        go.Surface(
            x=lon_grid,
            y=lat_grid,
            z=z_flat,
            surfacecolor=bathy_vals_ds,
            colorscale="Blues_r",
            cmin=np.nanmin(bathy_vals_ds),
            cmax=0,
            showscale=True,
            colorbar=dict(
                title=dict(text="Depth (m)", side="top"),
                orientation="h",
                thickness=15,
                len=0.4,
                x=0.5,
                xanchor="center",
                y=-0.05,
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


# ---------------------------------------------------------------------------
# Core figure builder  —  now accepts a list of trace dicts
# ---------------------------------------------------------------------------


def make_figure(
    traces: list[dict],
    title: str,
    colorscale: str,
) -> go.Figure:
    """
    Build a 3-D scatter figure with one Scatter3d trace per entry in *traces*.

    Each entry must contain:
        lon, lat, depth  – 1-D array-like
        color            – 1-D array-like (values that drive the colorscale)
        label            – str shown in the legend / hover

    The map floor is drawn using the combined extent of all traces.
    """
    fig = go.Figure()

    all_lon, all_lat, all_depth = [], [], []

    for trace in traces:
        lon = np.asarray(trace["lon"])
        lat = np.asarray(trace["lat"])
        depth = np.asarray(trace["depth"])
        color = np.asarray(trace["color"])
        label = trace.get("label", "")

        all_lon.append(lon)
        all_lat.append(lat)
        all_depth.append(depth)

        fig.add_trace(
            go.Scatter3d(
                x=lon,
                y=lat,
                z=depth,
                name=label,
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
        )

    # Map floor uses the combined bounding box of every trace
    combined_lon = np.concatenate(all_lon)
    combined_lat = np.concatenate(all_lat)
    combined_depth = np.concatenate(all_depth)

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
    fig = add_map_floor(fig, combined_lon, combined_lat, combined_depth)
    # fig = add_bathy_contours(fig, combined_lon, combined_lat, combined_depth, 250)
    # fig = add_bathy_heatmap(fig, combined_lon, combined_lat, combined_depth)
    return fig


# ---------------------------------------------------------------------------
# Dash dashboard  —  gains a Mission dropdown at the top of the chain
# ---------------------------------------------------------------------------


def create_dashboard(
    missions: "xr.DataTree | list[xr.DataTree]",
    port: int = 8050,
    debug: bool = True,
):
    """
    Interactive 3-D payload dashboard.  Accepts one mission or a list.

    Dropdown chain:
      Mission → Sensor → Variable → Colour Scale

    When more than one mission is loaded the Mission dropdown gains an
    "All Missions" entry at the top.  Selecting it overlays every mission
    on a single plot using the sensor/variable that are common to all of
    them.  Each mission becomes a separately labelled trace so they can be
    toggled on/off via the Plotly legend.
    """
    mission_list = _normalise_missions(missions)

    # ── Build per-mission sensor/variable lookup ──────────────────────────
    # { mission_name: { sensor_name: { var_name: DataArray } } }
    all_sensor_vars: dict[str, dict[str, dict]] = {}
    for m in mission_list:
        name = m.attrs.get("name", f"mission_{len(all_sensor_vars)}")
        all_sensor_vars[name] = build_sensor_vars(m)

    # Keep a name→DataTree map for coord lookups
    mission_map: dict[str, xr.DataTree] = {
        m.attrs.get("name", f"mission_{i}"): m for i, m in enumerate(mission_list)
    }

    mission_names = list(all_sensor_vars.keys())
    multi = len(mission_names) > 1

    # ── Helpers that respect the __all__ sentinel ─────────────────────────

    def _shared_sensors() -> list[str]:
        """Sensors present in every mission (preserves insertion order)."""
        sets = [set(all_sensor_vars[n].keys()) for n in mission_names]
        shared = sets[0].intersection(*sets[1:])
        # Return in the order they appear in the first mission
        return [s for s in all_sensor_vars[mission_names[0]] if s in shared]

    def _shared_variables(sensor: str) -> list[str]:
        """Variables for *sensor* present in every mission."""
        sets = [
            set(all_sensor_vars[n][sensor].keys())
            for n in mission_names
            if sensor in all_sensor_vars[n]
        ]
        if not sets:
            return []
        shared = sets[0].intersection(*sets[1:])
        return [v for v in all_sensor_vars[mission_names[0]][sensor] if v in shared]

    def sensor_opts(mission_name: str) -> list[dict]:
        sensors = (
            _shared_sensors()
            if mission_name == _ALL
            else list(all_sensor_vars[mission_name].keys())
        )
        return [{"label": s, "value": s} for s in sensors]

    def variable_opts(mission_name: str, sensor: str) -> list[dict]:
        variables = (
            _shared_variables(sensor)
            if mission_name == _ALL
            else list(all_sensor_vars[mission_name][sensor].keys())
        )
        return [{"label": v, "value": v} for v in variables]

    # ── Initial dropdown state ────────────────────────────────────────────
    # Default to "All Missions" when multiple missions are loaded
    initial_mission = _ALL if multi else mission_names[0]
    initial_sensors = sensor_opts(initial_mission)
    initial_sensor = initial_sensors[0]["value"]
    initial_vars = variable_opts(initial_mission, initial_sensor)
    initial_var = initial_vars[0]["value"]

    mission_options = (
        (
            [{"label": "All Missions", "value": _ALL}]
            + [{"label": n, "value": n} for n in mission_names]
        )
        if multi
        else [{"label": mission_names[0], "value": mission_names[0]}]
    )

    colorscale_options = [{"label": cs, "value": cs} for cs in COLOUR_SCALES]

    # ── Layout ────────────────────────────────────────────────────────────
    app = Dash(__name__, title="MAMMA MIA Payload Simulator")
    app.layout = html.Div(
        style={
            "fontFamily": "sans-serif",
            "padding": "16px",
            "backgroundColor": "#f8f9fa",
        },
        children=[
            html.H2("Payload Dashboard", style={"marginBottom": "4px"}),
            html.Hr(),
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
                            html.Label("Mission", style={"fontWeight": "bold"}),
                            dcc.Dropdown(
                                id="mission-dropdown",
                                options=mission_options,
                                value=initial_mission,
                                clearable=False,
                                style={"minWidth": "180px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Sensor", style={"fontWeight": "bold"}),
                            dcc.Dropdown(
                                id="sensor-dropdown",
                                options=initial_sensors,
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
                                options=initial_vars,
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
            dcc.Graph(
                id="payload-plot", style={"height": "75vh"}, config={"scrollZoom": True}
            ),
        ],
    )

    # ── Callbacks ─────────────────────────────────────────────────────────

    @app.callback(
        Output("sensor-dropdown", "options"),
        Output("sensor-dropdown", "value"),
        Input("mission-dropdown", "value"),
    )
    def update_sensor_options(mission_name: str):
        opts = sensor_opts(mission_name)
        return opts, opts[0]["value"]

    @app.callback(
        Output("variable-dropdown", "options"),
        Output("variable-dropdown", "value"),
        Input("mission-dropdown", "value"),
        Input("sensor-dropdown", "value"),
    )
    def update_variable_options(mission_name: str, sensor: str):
        opts = variable_opts(mission_name, sensor)
        return opts, opts[0]["value"]

    @app.callback(
        Output("payload-plot", "figure"),
        Input("mission-dropdown", "value"),
        Input("sensor-dropdown", "value"),
        Input("variable-dropdown", "value"),
        Input("colorscale-dropdown", "value"),
    )
    def update_plot(mission_name: str, sensor: str, variable: str, colorscale: str):
        if not all([mission_name, sensor, variable]):
            return go.Figure()

        if mission_name == _ALL:
            # Build one trace per mission, overlay on a single figure
            traces = []
            for name in mission_names:
                if sensor not in all_sensor_vars[name]:
                    continue
                if variable not in all_sensor_vars[name][sensor]:
                    continue
                lon, lat, depth = get_coords(mission_map[name], sensor)
                color = np.array(all_sensor_vars[name][sensor][variable].values)
                traces.append(
                    {
                        "lon": lon,
                        "lat": lat,
                        "depth": depth,
                        "color": color,
                        "label": name,
                    }
                )
            title = f"All Missions — {sensor}: {variable}"
        else:
            lon, lat, depth = get_coords(mission_map[mission_name], sensor)
            color = np.array(all_sensor_vars[mission_name][sensor][variable].values)
            traces = [
                {
                    "lon": lon,
                    "lat": lat,
                    "depth": depth,
                    "color": color,
                    "label": mission_name,
                }
            ]
            title = f"{mission_name} — {sensor}: {variable}"

        fig = make_figure(traces, title, colorscale)
        logger.info(
            f"Plot updated — mission={mission_name} sensor={sensor} variable={variable}"
        )
        return fig

    app.run(debug=debug, port=port, use_reloader=False)


# ---------------------------------------------------------------------------
# start_payload_dashboard  —  accepts one or many missions
# ---------------------------------------------------------------------------


def start_payload_dashboard(
    missions: "xr.DataTree | list[xr.DataTree]",
    parameter: str | None = None,
    in_app: bool = False,
    port: int = 8050,
):
    """
    Launch an interactive payload dashboard or return a static figure.

    Parameters
    ----------
    missions : xr.DataTree or list[xr.DataTree]
        One mission or a list.  When multiple missions are supplied and
        *parameter* is also set, all missions are overlaid on a single static
        figure (one trace per mission, same sensor/variable assumed to exist
        in each).
    parameter : str, optional
        If given, produces a static figure instead of a Dash app.
    in_app : bool, optional
        Return the figure rather than calling fig.show().
    port : int, optional
        Dash server port when parameter is None.
    """
    logger.info("starting payload dashboard...")
    mission_list = _normalise_missions(missions)

    if parameter is None:
        # Full interactive dashboard
        create_dashboard(mission_list, port=port)
    else:
        # Static multi-mission overlay
        traces = []
        for i, mission in enumerate(mission_list):
            name = mission.attrs.get("name", f"mission_{i}")
            color = np.array(mission.payload[parameter][:])
            traces.append(
                {
                    "lon": np.array(mission.payload["longitude"][:]),
                    "lat": np.array(mission.payload["latitude"][:]),
                    "depth": np.array(mission.payload["depth"][:]),
                    "color": color,
                    "label": name,
                }
            )

        title = f"Payload: {parameter}"
        fig = make_figure(traces, title, colorscale="Jet")

        if not in_app:
            fig.show()
        else:
            return fig


# ---------------------------------------------------------------------------
# plot_path  —  accepts one or many missions, one coloured trace each
# ---------------------------------------------------------------------------


def plot_path(
    missions: "xr.DataTree | list[xr.DataTree]",
    colour_scale: str = "Viridis",
):
    """
    Interactive 3-D trajectory plot, coloured by datetime.

    Accepts a single DataTree or a list — each mission becomes its own
    Scatter3d trace with a separate colour axis, labelled by mission name.

    Args:
        missions:     One DataTree or a list of DataTrees.
        colour_scale: Plotly colourscale name for the time colouring.
    """
    mission_list = _normalise_missions(missions)

    fig = go.Figure()

    all_lon, all_lat, all_depth = [], [], []

    for i, mission in enumerate(mission_list):
        if not isinstance(mission, xr.DataTree):
            raise TypeError(f"Expected DataTree, got {type(mission)}")

        name = mission.attrs.get("name", f"mission_{i}")
        lon = np.array(mission.payload["ctd"]["longitude"])
        lat = np.array(mission.payload["ctd"]["latitude"])
        depth = np.array(mission.payload["ctd"]["depth"])
        time = np.array(mission.payload["ctd"].time).tolist()

        all_lon.append(lon)
        all_lat.append(lat)
        all_depth.append(depth)

        # Each mission gets its own showscale=True only for the first trace
        # to avoid cluttering with N identical colour bars.
        fig.add_trace(
            go.Scatter3d(
                x=lon,
                y=lat,
                z=depth,
                name=name,
                mode="markers",
                marker=dict(
                    size=2,
                    color=time,
                    colorscale=colour_scale,
                    opacity=0.8,
                    colorbar=dict(
                        thickness=20,
                        title=dict(text="Time"),
                        # Stack colour bars vertically when there are multiple traces
                        x=1.0 + i * 0.12,
                    ),
                    showscale=True,
                ),
            )
        )

    combined_lon = np.concatenate(all_lon)
    combined_lat = np.concatenate(all_lat)
    combined_depth = np.concatenate(all_depth)

    fig.update_scenes(zaxis_autorange="reversed")
    fig.update_layout(
        title=dict(
            text="Glider Trajectory", font=dict(size=30), automargin=True, yref="paper"
        ),
        scene=dict(
            xaxis_title="longitude",
            yaxis_title="latitude",
            zaxis_title="depth",
        ),
    )

    # Reuse the existing map-floor helper with the combined extent
    fig = add_map_floor(fig, combined_lon, combined_lat, combined_depth)

    fig.show()
    logger.success("successfully created platform path plot.")
