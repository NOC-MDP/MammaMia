from mamma_mia import Mission
from dataclasses import dataclass

@dataclass
class Campaign:
    name: str
    description: str
    missions: dict[str, Mission]
