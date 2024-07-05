from dataclasses import dataclass,field
from pyinterp import RTree

@dataclass
class Meta:
    description: str
    zarr_path: str


@dataclass
class Model:
    name: str
    #zarr: zarr.Group = field(init=False)
    tree: RTree = field(init=False)
    #meta: Meta

    def __post_init__(self):
        self.tree = RTree()
        #self.zarr = zarr.group()