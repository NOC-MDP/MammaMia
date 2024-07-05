from dataclasses import dataclass

@dataclass
class SensorSuite():
    name: str
    temperature: bool = False
    salinity: bool = False
    u_component: bool = False
    v_component: bool = False

@dataclass
class CTD(SensorSuite):
    name = "CTD"
    temperature = True
    salinity = True

@dataclass
class ADCP(SensorSuite):
    name = "ADCP"
    u_component: True
    v_component: True

Sensors = CTD | ADCP