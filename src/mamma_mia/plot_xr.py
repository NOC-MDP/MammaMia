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

import numpy as np
import plotly.graph_objects as go
import xarray as xr
from dash import Dash, Input, Output, callback, dcc, html
from loguru import logger

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
        uirevision="constant",  # Keeps camera angle stable between updates
    )
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
            html.H2("Payload Dashboard", style={"marginBottom": "4px"}),
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
