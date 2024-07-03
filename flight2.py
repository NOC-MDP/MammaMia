from dataclasses import dataclass
import numpy as np
import zarr
from pyinterp import RTree


@dataclass(frozen=True)
class DTCoordinate:
    latitude: np.double
    longitude: np.double
    depth: np.double
    datetime: np.datetime64

        
@dataclass()
class Trajectory:
    id: int
    dtcoordinates: np.ndarray[DTCoordinate]


@dataclass()
class Autosub:
    id: int


@dataclass()
class Slocum:
    id: int


AUVs = Autosub | Slocum


@dataclass(frozen=True)
class AUV:
    id: int
    type: AUVs

    def __post_init__(self):
        match self.type:
            case Autosub():
                print(f"autosub! {self.type.id}")
            case Slocum():
                print(f"slocum! {self.type.id}")
            case _:
                raise Exception("unknown type")


@dataclass(frozen=True)
class Model:
    zarr: zarr.group
    tree: RTree
    meta: str


@dataclass(frozen=True)
class TEntry:
    temperature: np.double


@dataclass(frozen=True)
class TSEntry:
    temperature: np.double
    salinity: np.double


DataEntry = TEntry | TSEntry


@dataclass()
class Reality:
    id: int
    models: np.ndarray[Model]
    data: np.ndarray[DataEntry]


@dataclass()
class Flight:
    id: int
    description: str
    trajectory: Trajectory
    auv: AUV
    reality: Reality


A = AUV(id=1,type=Autosub(id=1))
B = AUV(id=2,type=Slocum(id=2))
