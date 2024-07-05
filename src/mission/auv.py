from dataclasses import dataclass

@dataclass
class AUV:
    name: str = ""


@dataclass
class Autosub(AUV):
    def __init__(self, name):
        super().__init__()
        self.name = "Autosub " + name


@dataclass
class Slocum(AUV):
    def __init__(self, name):
        super().__init__()
        self.name = "Slocum " + name


AUVs = Autosub | Slocum

