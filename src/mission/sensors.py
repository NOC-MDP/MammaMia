from dataclasses import dataclass, field
from abc import ABC


class SensorSuite(dict):
    def __setitem__(self, key, value):
        if not isinstance(value, SensorGroup):
            raise TypeError(f"Value must be an instance of SensorGroup, not {type(value).__name__}")
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value


@dataclass
class Sensor(ABC):
    name: str
    units: str


@dataclass
class Temperature(Sensor):
    name: str = "temperature"
    units: str = "degreesC"


@dataclass
class Salinity(Sensor):
    name: str = "salinity"
    units: str = "PSU"


@dataclass
class Ucomponent(Sensor):
    name: str = "ucomponent"
    units: str = "ms-1"


@dataclass
class Vcomponent(Sensor):
    name: str = "vcomponent"
    units: str = "ms-1"


@dataclass
class SensorGroup(ABC):
    name: str
    sensors: dict[str, Sensor] = field(default_factory=dict)


@dataclass
class CTD(SensorGroup):
    name: str = "CTD"

    def __post_init__(self):
        self.sensors = {"temperature": Temperature(),"salinity": Salinity()}


@dataclass
class ADCP(SensorGroup):
    name: str = "ADCP"

    def __post_init__(self):
        self.sensors = {"Ucomponent": Ucomponent(),"Vcomponent": Vcomponent(),}
