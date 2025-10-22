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
from unittest import case

from attrs import frozen, define
from loguru import logger
from enum import Enum
import os

class ResolutionType(Enum):
    """
    Resolution type enumeration: this determines the world resolution.
    """
    QuarterDegree = "eORCA025"
    OneDegree = "eORCA1"
    TwelfthDegree = "eORCA12"
    @classmethod
    def from_string(cls, string:str) -> "ResolutionType":
        match string:
            case "025" | "eorca025":
                return ResolutionType.QuarterDegree
            case "1" | "eorca1":
                return ResolutionType.OneDegree
            case "12" | "eorca12":
                return ResolutionType.TwelfthDegree
            case _:
                raise ValueError(f"Invalid resolution string: {string}")

@frozen
class ResolutionTypeWithRank:
    resolution_type: ResolutionType
    rank: int
    @classmethod
    def from_string(cls,enum_string:str) -> "ResolutionTypeWithRank":
        match enum_string:
            case "12" | "eorca12":
                return cls(resolution_type=ResolutionType.TwelfthDegree, rank=1)
            case "025" | "eorca025":
                return cls(resolution_type=ResolutionType.QuarterDegree, rank=2)
            case "1" | "eorca1":
                return cls(resolution_type=ResolutionType.OneDegree, rank=3)
            case _:
                raise ValueError(f"unknown resolution type {enum_string}")
    @classmethod
    def from_string_and_rank(cls, enum_string:str,rank:int) -> "ResolutionTypeWithRank":
        match enum_string:
            case "12" | "eorca12":
                return cls(resolution_type=ResolutionType.TwelfthDegree, rank=rank)
            case "025" | "eorca025":
                return cls(resolution_type=ResolutionType.QuarterDegree, rank=rank)
            case "1" | "eorca1":
                return cls(resolution_type=ResolutionType.OneDegree, rank=rank)
            case _:
                raise ValueError(f"unknown resolution type {enum_string}")

class SourceType(Enum):
    """
    Source type enumeration: this determines where worlds are sourced from
    """
    CMEMS = "cmems"
    MSM = "msm"
    LOCAL = "local"
    @classmethod
    def from_string(cls,enum_string:str) -> "SourceType":
        match enum_string:
            case "cmems" | "CMEMS":
                return SourceType.CMEMS
            case "msm" | "MSM":
                return SourceType.MSM
            case "local" | "LOCAL":
                return SourceType.LOCAL
            case _:
                raise ValueError(f"unknown source type {enum_string}")

@frozen
class SourceConfig:
    """

    """
    source_type: SourceType
    local_dir: str = None
    @classmethod
    def from_string(cls,src_str:str):
        match src_str:
            case "cmems" | "CMEMS" | "MSM" | "msm":
                logger.info(f"setting source type to {src_str}")
                return cls(source_type=SourceType.from_string(src_str))
            case "local" | "LOCAL":
                logger.info(f"setting source type to {src_str}")
                return cls(source_type=SourceType.from_string("LOCAL"),local_dir=os.getcwd())
            case _:
                if os.path.isdir(src_str):
                    logger.info(f"setting source location to {src_str}")
                    return cls(source_type=SourceType.LOCAL, local_dir=src_str)
                else:
                    raise ValueError(f"{src_str} is not a valid directory or source type")

class FieldType(Enum):
    """
    Field type enumeration: this determines what field type the world is made up of
    """
    one_hour_instant = "PT1H-i"
    six_hour_instant = "PT6H-i"
    six_hour_mean = "PT6H-m"
    daily_mean = "P1D-m"
    five_day_mean = "P5D-m"
    monthly_mean = "P1M-m"
    annual_mean = "P1A-m"
    @classmethod
    def from_string(cls,enum_string:str) -> "FieldType":
        match enum_string:
            case "PT1H-i":
                return FieldType.one_hour_instant
            case "PT6H-i":
                return FieldType.six_hour_instant
            case "PT6H-m":
                return FieldType.six_hour_mean
            case "P1D-m":
                return FieldType.daily_mean
            case "P5D-m" | "5-day":
                return FieldType.five_day_mean
            case "P1M-m" | "monthly":
                return FieldType.monthly_mean
            case "P1A-m" | "annual":
                return FieldType.annual_mean
            case _:
                raise ValueError(f"unknown field type {enum_string}")

@frozen
class FieldTypeWithRank:
    """
    Field type with ranking: This class wraps the FieldType enum, ranking determines which world MM will use as a preference.
    If the from_string method is used MM will favour higher temporal and instantaneous fields. If from string and rank method
    is used then the user can set a specific rank (lower is better).
    """
    field_type: FieldType
    rank: int
    @classmethod
    def from_string(cls,enum_string:str) -> "FieldTypeWithRank":
        match enum_string:
            case "PT1H-i":
                return cls(field_type=FieldType.one_hour_instant, rank=1)
            case "PT6H-i":
                return cls(field_type=FieldType.six_hour_instant, rank=2)
            case "PT6H-m":
                return cls(field_type=FieldType.six_hour_mean, rank=3)
            case "P1D-m":
                return cls(field_type=FieldType.daily_mean, rank=4)
            case "P5D-m" | "5-day":
                return cls(field_type=FieldType.five_day_mean, rank=5)
            case "P1M-m" | "monthly":
                return cls(field_type=FieldType.monthly_mean, rank=6)
            case "P1A-m" | "annual":
                return cls(field_type=FieldType.annual_mean, rank=7)
            case _:
                raise ValueError(f"unknown field type {enum_string}")
    @classmethod
    def from_string_and_rank(cls, enum_string:str,rank:int) -> "FieldTypeWithRank":
        match enum_string:
            case "PT1H-i":
                return cls(field_type=FieldType.one_hour_instant, rank=rank)
            case "PT6H-i":
                return cls(field_type=FieldType.six_hour_instant, rank=rank)
            case "PT6H-m":
                return cls(field_type=FieldType.six_hour_mean, rank=rank)
            case "P1D-m":
                return cls(field_type=FieldType.daily_mean, rank=rank)
            case "P5D-m" | "5-day":
                return cls(field_type=FieldType.five_day_mean, rank=5)
            case "P1M-m":
                return cls(field_type=FieldType.monthly_mean, rank=rank)
            case "P1A-m" | "annual":
                return cls(field_type=FieldType.annual_mean, rank=rank)
            case _:
                raise ValueError(f"unknown field type {enum_string}")

# TODO figure out why only domains that work are global
class DomainType(Enum):
    """
    Domain type enumeration: sets the domain of the world.
    """
    globe = "glo"
    regional = "regional"
    #arctic = "arc"
    @classmethod
    def from_string(cls,enum_string:str) -> "DomainType":
        match enum_string:
            case "glo":
                logger.info("setting domain type to glo")
                return DomainType.globe
            case "regional":
                logger.info("setting domain type to regional")
                return DomainType.regional
            case _:
                raise ValueError(f"unknown domain type {enum_string}")

class WorldType(Enum):
    """
    World type enumeration: this determines if a world is derived from a model or observations
    """
    model = "mod"
    observation = "obs"
    obs_mob = "obs-mob"
    @classmethod
    def from_string(cls,enum_string:str) -> "WorldType":
        match enum_string:
            case "mod":
                logger.info("setting world type to model")
                return WorldType.model
            case "obs":
                logger.info("setting world type to observation")
                return WorldType.observation
            case _:
                raise ValueError(f"unknown world type {enum_string}")

@frozen
class WorldExtent:
    lat_max: float
    lat_min: float
    lon_max: float
    lon_min: float
    time_start: str
    time_end: str
    depth_max: float

@define
class WorldsAttributes:
    extent: WorldExtent
    interpolator_priorities: dict
    matched_worlds: dict

@define
class WorldsConf:
    attributes: WorldsAttributes
    worlds: dict
    stores: dict

@frozen
class MatchedWorld:
    """
    MatchedWorld class: this is created when a world is matched containing parameters allowing it to be downloaded from its
    source
    """
    data_id: str
    world_type: WorldType
    domain: DomainType
    dataset_name: str
    resolution: ResolutionTypeWithRank
    alternative_parameter: dict | None
    field_type: FieldTypeWithRank
    variable_alias: dict
    local_dir: str = None

    def __attrs_post_init__(self):
        # TODO add some validation here
        pass

