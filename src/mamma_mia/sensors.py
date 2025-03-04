from dataclasses import dataclass, InitVar, field
from mamma_mia import parameters


@dataclass(frozen=True)
class Sensor:
    """
    Immutable Sensor class that represents a single sensor in a sensor array
    """
    type: str
    units: str


@dataclass
class CTD:
    """
    Immutable sensor array that represents a CTD array, i.e. contains temperature, salinity and pressure sensors

    Returns:
        CTD sensor array class with auto generated uuid.
    """
    sample_rate_temp: InitVar[float]
    sample_rate2: InitVar[float]
    sample_rate3: InitVar[float]
    sensor1: Sensor
    sensor2: Sensor
    sensor3: Sensor
    array: str = "CTD"

    def __post_init__(self,
                      sample_rate_temp=1.0,
                      sample_rate2=1.0,
                      sample_rate3=1.0
                      ):
        self.sensor1 = Sensor(type="temperature", units="degreesC")
        self.sensor2 = Sensor(type="salinity", units="PSU")
        self.sensor3 = Sensor(type="pressure", units="Pa")


@dataclass(frozen=True)
class BIO:
    """
    Immutable sensor array that represents a biological sensor array, i.e. it contains nitrate, silicate and phosphate sensors

    Returns:
        BIO sensor array class with auto generated uuid.
    """
    array: str = "BIO"
    uuid: uuid = uuid.uuid4()
    sensor1: Sensor = Sensor(type="nitrate", units="mmol kg-3")
    sensor2: Sensor = Sensor(type="silicate", units="mmol kg-3")
    sensor3: Sensor = Sensor(type="phosphate", units="mmol kg-3")


@dataclass(frozen=True)
class ADCP:
    """
    Immutable sensor array that represents a biological sensor array, i.e. it contains nitrate, silicate and phosphate sensors

    Returns:
        BIO sensor array class with auto generated uuid.
    """
    array: str = "ADCP"
    uuid: uuid = uuid.uuid4()
    sensor1: Sensor = Sensor(type="u_component", units="ms-1")
    sensor2: Sensor = Sensor(type="v_component", units="ms-1")
    sensor3: Sensor = Sensor(type="w_component", units="ms-1")


@dataclass
class Sensor2:
    # instance parameters
    sensor_serial_number: str
    bodc_sensor_version_id: int
    bodc_sensor_id: int
    sensor_name: str
    # type parameters
    bodc_sensor_model_id: int
    bodc_sensor_model_registry_id: int
    instrument_type: str
    sensor_manufacturer: str
    model_name: str
    sensor_model: str
    parameters: dict = field(default_factory=dict)

    def __post_init__(self):
        # Ensure all values in the parameters dictionary are instances of Parameter
        for key, value in self.parameters.items():
            if not isinstance(value, parameters.Parameter):  # Runtime type check
                raise TypeError(f"Parameter '{key}' must be an instance of parameters.Parameter, got {type(value)}")


@dataclass
class WETlabsFluor(Sensor2):
    bodc_sensor_model_id: int = 622
    bodc_sensor_model_registry_id: int = 259
    instrument_type: str = "radiometers"
    sensor_manufacturer: str = "WET Labs"
    model_name: str = "WET Labs {Sea-Bird WETLabs} ECO Puck Triplet FLBBCD-SLC scattering fluorescence sensor"
    sensor_model: str = "WETLabs ECO Puck Triplet FLBBCD-SLC scattering fluorescence sensor"

    def __post_init__(self):
        self.parameters = {"chlor_conc": parameters.CHLA, "diss_org_mat": parameters.CDOM, "back_atten": parameters.BBP700}

WET_Labs_FLBBCD_SLC_3289 = WETlabsFluor(
    bodc_sensor_id=638,
    bodc_sensor_version_id=1095,
    sensor_name="WET Labs FLBBCD-SLC 3289",
    sensor_serial_number="3289"
)


@dataclass
class SBEgliderCTD(Sensor2):
    bodc_sensor_model_id: int = field(default=485,init=False)
    bodc_sensor_model_registry_id: int = field(default=242,init=False)
    instrument_type: str = field(default="water temperature sensor",init=False)
    sensor_manufacturer: str = field(default="Sea-Bird Scientific",init=False)
    model_name: str = field(default="SBE Slocum Glider Payload (GPCTD) CTD",init=False)
    sensor_model: str = field(default="SBE Slocum Glider Payload (GPCTD) CTD",init=False)

    def __post_init__(self):
        self.parameters = {"Salinty": parameters.CNDC, "Pressure": parameters.PRES, "Temperature": parameters.TEMP}


@dataclass
class SBE52mpCTD(Sensor2):
    bodc_sensor_model_id: int = field(default=681, init=False)
    bodc_sensor_model_registry_id: int = field(default=273,init=False)
    instrument_type:str = field(default="CTD", init=False)
    sensor_manufacturer:str = field(default="Sea-Bird Scientific",init=False)
    model_name:str = field(default="Sea-Bird SBE 52-MP moored profiler CTD",init=False)
    sensor_model:str = field(default="Sea-Bird SBE 52-MP moored profiler CTD",init=False)

    def __post_init__(self):
        self.parameters = {"Salinty": parameters.CNDC, "Pressure": parameters.PRES, "Temperature": parameters.TEMP}


SBE_GLIDER_CTD_9099 = SBEgliderCTD(
    sensor_serial_number="9099",
    bodc_sensor_version_id=1304,
    bodc_sensor_id=847,
    sensor_name="SBE Glider Payload CTD 9099",
)


SBE_GLIDER_CTD_9100 = SBEgliderCTD(
    sensor_serial_number="9100",
    bodc_sensor_version_id=1130,
    bodc_sensor_id=677,
    sensor_name="SBE Glider Payload CTD 9100",
)


SBE_52MP_CTD_0221 = SBE52mpCTD(
    sensor_serial_number="0221",
    bodc_sensor_version_id=1661,
    bodc_sensor_id=1229,
    sensor_name="SBE 52-MP CTD 0221"
)


SBE_52MP_CTD_0222 = SBE52mpCTD(
    sensor_serial_number="0222",
    bodc_sensor_version_id=1662,
    bodc_sensor_id=1230,
    sensor_name="SBE 52-MP CTD 0222"
)
