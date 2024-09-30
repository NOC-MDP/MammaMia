from dataclasses import dataclass
from collections import namedtuple
import uuid

@dataclass(frozen=True)
class Sensor:
    """
    class for all sensor types.
    """
    type: str
    units: str

CTD = { "sensors":
            {   "sensor1": Sensor(type="temperature",units="degreesC"),
                "sensor2": Sensor(type="salinity",units="PSU"),
                "sensor3": Sensor(type="pressure",units="bar"),
            },
        "uuid": uuid.uuid4()
}

BIO = { "sensors":
            {   "sensor1": Sensor(type="silicate",units="mmol kg-3"),
                "sensor2": Sensor(type="nitrate",units="mmmol kg-3"),
                "sensor3": Sensor(type="phosphate",units="mmol kg-3"),
            },
        "uuid": uuid.uuid4()
}

