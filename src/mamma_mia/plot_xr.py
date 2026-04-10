import numpy as np
import plotly.graph_objects as go
import xarray as xr
from loguru import logger


def plot_payload(mission: xr.DataTree, parameter=None, in_app: bool = False):
    """
    Creates an interactive plot of the AUV trajectory with the given parameters data mapped onto it using the
    specified colour map.

    Returns:
        Interactive plotly figure that opens in a web browser.
    """
    # Example parameters for the dropdown
    # Example parameters and their expected value ranges (cmin and cmax)
    parameters = {}
    if parameter is None:
        for key, payload in mission.payload["ctd"].items():
            parameters[key] = {
                "cmin": np.nanmin(payload.values),
                "cmax": np.nanmax(payload.values),
            }

        # List of available color scales for the user to choose from
        colour_scales = [
            "Jet",
            "Viridis",
            "Cividis",
            "Plasma",
            "Rainbow",
            "Portland",
        ]

        # Initial setup: first parameter and color scale
        initial_parameter = next(iter(mission.payload["ctd"].keys()))
        initial_colour_scale = "Jet"

        marker = {
            "size": 2,
            "color": np.array(
                mission.payload["ctd"][initial_parameter].values
            ),  # Ensuring its serializable
            "colorscale": initial_colour_scale,
            "cmin": parameters[initial_parameter][
                "cmin"
            ],  # Set the minimum value for the color scale
            "cmax": parameters[initial_parameter][
                "cmax"
            ],  # Set the maximum value for the color scale
            "opacity": 0.8,
            "colorbar": {"thickness": 40},
        }

        title = {
            "text": f"Payload: {initial_parameter}",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper",
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }

        y = mission.payload["ctd"]["latitude"].values
        x = mission.payload["ctd"]["longitude"].values
        z = mission.payload["ctd"]["depth"].values
        # Create the initial figure
        fig = go.Figure(
            data=[go.Scatter3d(x=x, y=y, z=z, mode="markers", marker=marker)]
        )

        # Update the scene and layout
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        # TODO fix the interaction between colour scales and parameters colour scale is not maintained when changing parameter
        # TODO it will always default to Jet colourscale
        # Define the dropdown for parameter selection
        parameter_dropdown = [
            {
                "args": [
                    {
                        "x": [
                            mission.payload["ctd"]["longitude"].values
                        ],  # Update x-coordinates
                        "y": [
                            mission.payload["ctd"]["latitude"].values
                        ],  # Update y-coordinates
                        "z": [mission.payload["ctd"]["depth"].values],
                        "marker.color": [
                            np.array(mission.payload["ctd"][parameter].values)
                        ],
                        # Update the color for the new parameter
                        "marker.cmin": parameters[parameter][
                            "cmin"
                        ],  # Set cmin for the new parameter
                        "marker.cmax": parameters[parameter][
                            "cmax"
                        ],  # Set cmax for the new parameter
                        "marker.colorscale": initial_colour_scale,
                    },
                    # Keep the initial color scale (can be updated below)
                    {
                        "title.text": f"Glider Payload: {parameter}"
                    },  # Update the title to reflect the new parameter
                ],
                "label": parameter,
                "method": "update",
            }
            for parameter in parameters
        ]

        # Define the dropdown for color scale selection
        color_scale_dropdown = [
            {
                "args": [
                    {
                        "marker.colorscale": colour_scale
                    }  # Update the color scale for the current parameter
                ],
                "label": colour_scale,
                "method": "restyle",
            }
            for colour_scale in colour_scales
        ]
        # Create text boxes for user to input cmin and cmax
        fig.update_layout(
            annotations=[
                # Add labels for dropdowns
                dict(
                    text="Sensor:",
                    x=0.05,
                    y=1.2,
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    font=dict(size=14),
                ),
                dict(
                    text="Color Scale:",
                    x=0.05,
                    y=1.15,
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    font=dict(size=14),
                ),
            ]
        )

        # Add both dropdowns to the layout
        fig.update_layout(
            updatemenus=[
                {
                    "buttons": parameter_dropdown,
                    "direction": "down",
                    "showactive": True,
                    "x": 0.10,  # Adjust position for the parameter dropdown
                    "xanchor": "left",
                    "y": 1.20,
                    "yanchor": "top",
                },
                {
                    "buttons": color_scale_dropdown,
                    "direction": "down",
                    "showactive": True,
                    "x": 0.10,  # Adjust position for the color scale dropdown
                    "xanchor": "left",
                    "y": 1.15,
                    "yanchor": "top",
                },
            ]
        )
    else:
        parameters[parameter] = {
            "cmin": np.nanmin(mission.payload[parameter][:]),
            "cmax": np.nanmax(mission.payload[parameter][:]),
        }

        # List of available color scales for the user to choose from
        # colour_scales = ["Jet", "Viridis", "Cividis", "Plasma", "Rainbow", "Portland"]

        # Initial setup: first parameter and color scale
        initial_colour_scale = "Jet"

        marker = {
            "size": 2,
            "color": np.array(
                mission.payload[parameter][:]
            ),  # Ensuring its serializable
            "colorscale": initial_colour_scale,
            "cmin": parameters[parameter][
                "cmin"
            ],  # Set the minimum value for the color scale
            "cmax": parameters[parameter][
                "cmax"
            ],  # Set the maximum value for the color scale
            "opacity": 0.8,
            "colorbar": {"thickness": 40},
        }

        title = {
            "text": f"Payload: {parameter}",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper",
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }
        # TODO figure out how to dynamically set these as they could be different parameters e.g. GLIDER_DEPTH
        if (
            mission.platform.attrs.platform_model == "Slocum_G2"
            or mission.platform.attrs.platform_model == "Slocum_G2_NonNMEA"
        ):
            latitude = "LATITUDE"
            longitude = "LONGITUDE"
            depth = "GLIDER_DEPTH"
        elif mission.platform.attrs.platform_model == "ALR_1500":
            latitude = "ALATPT01"
            longitude = "ALONPT01"
            depth = "ADEPPT01"
        else:
            raise Exception(
                f"unsupported platform {mission.platform.attrs.platform_type} for payload plotting"
            )

        y = mission.payload[latitude][:]
        x = mission.payload[longitude][:]
        z = mission.payload[depth][:]
        # Create the initial figure
        fig = go.Figure(
            data=[go.Scatter3d(x=x, y=y, z=z, mode="markers", marker=marker)]
        )
        # Update the scene and layout
        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
    if not in_app:
        fig.show()
    else:
        return fig
    logger.info("successfully plotted payloads")


def plot_trajectory(
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
