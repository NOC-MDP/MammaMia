from dataclasses import dataclass, field
from abc import ABC



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
    sensors: dict[str, Sensor] = field(init=False)

    def __post_init__(self):
        self.sensors = {"temperature": Temperature(),
                        "salinity": Salinity()
                        }


@dataclass
class ADCP(SensorGroup):
    name: str = "ADCP"
    sensors: dict[str, Sensor] = field(init=False)

    def __post_init__(self):
        self.sensors = {"Ucomponent": Ucomponent(),
                        "Vcomponent": Vcomponent(),
                        }


@dataclass
class SensorSuite:
    groups: dict[str, SensorGroup] = field(default_factory=dict)
