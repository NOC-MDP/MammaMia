from dataclasses import dataclass
from collections.abc import MutableMapping
from abc import ABC, abstractmethod

@dataclass
class SensorSuite(MutableMapping):
    """ A dictionary which contains only child classes of Sensor """
    def __init__(self, *args, **kwargs):
        self._data = dict()  # or collections.OrderedDict, etc.
        self.update(*args, **kwargs)

    def __iter__(self):
        return self._data.__iter__()

    def __setitem__(self, key, value):
        if not isinstance(value, Sensor):
            raise TypeError(repr(type(value)))
        self._data.__setitem__(key, value)

    def __delitem__(self, key):
        self._data.__delitem__(key)

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __len__(self):
        return self._data.__len__()

@dataclass
class Sensor(ABC):
    name: str

    @abstractmethod
    def print_name(self):
        pass


@dataclass
class CTD(Sensor):
    name = "CTD"
    temperature = True
    salinity = True

    def print_name(self):
        print(self.name)

    def do_nothing(self):
        pass

@dataclass
class ADCP(Sensor):
    name = "ADCP"
    u_component = True
    v_component = True

    def print_name(self):
        print(self.name)

