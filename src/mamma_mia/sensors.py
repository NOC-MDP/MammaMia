from dataclasses import dataclass
import uuid

@dataclass(frozen=True)
class Sensor:
    """
    Immutable Sensor class that represents a single sensor in a sensor array
    """
    type: str
    units: str

@dataclass(frozen=True)
class CTD:
    """
    Immutable sensor array that represents a CTD array, i.e. contains temperature, salinity and pressure sensors

    Returns:
        CTD sensor array class with auto generated uuid.
    """
    array: str = "CTD"
    uuid: uuid = uuid.uuid4()
    sensor1: Sensor =  Sensor(type="temperature",units="degreesC")
    sensor2: Sensor = Sensor(type="salinity",units="PSU")
    sensor3: Sensor = Sensor(type="pressure",units="bar")


@dataclass(frozen=True)
class BIO:
    """
    Immutable sensor array that represents a biological sensor array, i.e. it contains nitrate, silicate and phosphate sensors

    Returns:
        BIO sensor array class with auto generated uuid.
    """
    array: str = "BIO"
    uuid: uuid = uuid.uuid4()
    sensor1: Sensor = Sensor(type="nitrate",units="mmol kg-3")
    sensor2: Sensor = Sensor(type="silicate",units="mmol kg-3")
    sensor3: Sensor = Sensor(type="phosphate",units="mmol kg-3")


@dataclass(frozen=True)
class ADCP:
    """
    Immutable sensor array that represents a biological sensor array, i.e. it contains nitrate, silicate and phosphate sensors

    Returns:
        BIO sensor array class with auto generated uuid.
    """
    array: str = "ADCP"
    uuid: uuid = uuid.uuid4()
    sensor1: Sensor = Sensor(type="u_component",units="ms-1")
    sensor2: Sensor = Sensor(type="v_component",units="ms-1")
    sensor3: Sensor = Sensor(type="w_component",units="ms-1")
