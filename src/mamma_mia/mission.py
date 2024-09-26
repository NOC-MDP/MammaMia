import uuid
from dataclasses import dataclass,field
import numcodecs.pickles
import numpy as np
import plotly.graph_objects as go
from loguru import logger
from mamma_mia.world import World
from mamma_mia.trajectory import Trajectory
from mamma_mia.auv import AUV
from mamma_mia.realities import Reality
import zarr
import xarray as xr


@dataclass
class Mission:
    """
    Creates a mamma_mia object

    Parameters:
    - id
    - description
    - world
    - trajectory
    - glider
    -reality

    Returns:
    - Mission object that is ready for flight!
    """
    name: str
    description: str
    id: uuid.UUID = uuid.uuid4()
    world: World = field(init=False)
    trajectory: Trajectory = field(init=False)
    auv: AUV = field(init=False)
    reality: Reality = field(init=False)

    def __post_init__(self):
        logger.success(f"successfully created mission named: {self.name}")

    def add_trajectory(self, in_trajectory: Trajectory) -> ():
        self.trajectory = in_trajectory

    def add_world(self, in_world: World) -> ():
        self.world = in_world

    def add_auv(self, in_auv: AUV) -> ():
        self.auv = in_auv

    def add_reality(self, in_reality: Reality) -> ():
        self.reality = in_reality

    def populate_mission(self,auv:AUV,traj_path:str) -> ():
        logger.info(f"adding auv with id {auv.id}")
        self.add_auv(in_auv=auv)
        logger.success(f"added {self.auv.id} successfully to {self.name}")
        logger.info(f"adding trajectory located at: {traj_path}")
        self.add_trajectory(in_trajectory= Trajectory(glider_traj_path=traj_path))
        logger.success(f"added trajectory successfully to {self.name}")
        logger.info(f"adding reality based on trajectory")
        self.add_reality(in_reality=Reality(auv=self.auv, trajectory=self.trajectory))
        logger.success(f"added reality successfully to {self.name}")
        logger.info(f"building world for {self.name}")
        self.add_world(in_world=World(trajectory=self.trajectory,reality=self.reality))
        logger.success(f"world built successfully for {self.name}")

    def fly(self):
        logger.info(f"flying {self.name} using {self.auv.id}")
        flight = {
            "longitude": np.array(self.trajectory.longitudes),
            "latitude": np.array(self.trajectory.latitudes),
            "depth": np.array(self.trajectory.depths),
            "time": np.array(self.trajectory.datetimes, dtype='datetime64'),
        }
        for key in self.reality.array_keys():
            try:
                logger.info(f"flying through {key} world and creating reality")
                self.reality[key] = self.world.interpolator[key].quadrivariate(flight)
            except KeyError:
                logger.warning(f"no interpolator found for parameter {key}")

        logger.success(f"{self.name} flown successfully")

    def show_reality(self, parameter:str,colourscale:str="Jet"):
        logger.info(f"showing reality for parameter {parameter}")
        marker = {
            "size": 2,
            "color": self.reality[parameter],
            "colorscale": colourscale,
            "opacity": 0.8,
            "colorbar": {"thickness": 40}
        }
        title = {
            "text": f"Glider Reality: {parameter}",
            "font": {"size": 30},
            "automargin": True,
            "yref": "paper"
        }

        scene = {
            "xaxis_title": "longitude",
            "yaxis_title": "latitude",
            "zaxis_title": "depth",
        }
        fig = go.Figure(data=[
            go.Scatter3d(x=self.trajectory.longitudes, y=self.trajectory.latitudes, z=self.trajectory.depths,mode='markers', marker=marker),
            # TODO implement bathy surface plot
            #go.Surface()
        ])

        fig.update_scenes(zaxis_autorange="reversed")
        fig.update_layout(title=title, scene=scene)
        fig.show()
        logger.success(f"successfully plotted reality for parameter {parameter}")

    def export(self):
        logger.info(f"exporting mission {self.name} to {self.name}.zarr")
        export = zarr.open_group(f"{self.name}.zarr",mode='w')
        export.attrs["name"] = self.name
        export.attrs["description"] = self.description
        export.attrs["id"] = str(self.id)

        auv_exp = export.create_group("auv")
        auv_exp.attrs["id"] = self.auv.id
        auv_exp.attrs["type"] = self.auv.type
        auv_exp.attrs["sensor_suite"] = str(self.auv.sensor_suite)

        export["trajectory"] = self.trajectory
        export["reality"] = self.reality

        world_exp = export.create_group("world")
        world_exp.attrs["matched_worlds"] = self.world.matched_worlds
        world_exp.attrs["extent"] = self.world.extent.to_dict()
        world_exp.attrs["catalog_priorities"] = dict(self.world.catalog.priorities)
        world_exp.attrs["interpolator_priorities"] = dict(self.world.interpolator["priorities"])

        for key, value in self.world.items():
            world_exp[key] = value.to_zarr().ds


        logger.success(f"successfully exported {self.name}")
