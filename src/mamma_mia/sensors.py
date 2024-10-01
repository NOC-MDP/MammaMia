from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class Sensor:
    """
    class for all sensor types.
    """
    type: str
    units: str

@dataclass(frozen=True)
class CTD:
    name: str = "CTD"
    uuid: uuid = uuid.uuid4()
    sensor1: Sensor =  Sensor(type="temperature",units="degreesC")
    sensor2: Sensor = Sensor(type="salinity",units="PSU")
    sensor3: Sensor = Sensor(type="pressure",units="bar")


@dataclass(frozen=True)
class BIO:
    name: str = "BIO"
    uuid: uuid = uuid.uuid4()
    sensor1: Sensor = Sensor(type="nitrate",units="mmol kg-3")
    sensor2: Sensor = Sensor(type="silicate",units="mmol kg-3")
    sensor3: Sensor = Sensor(type="phosphate",units="mmol kg-3")



