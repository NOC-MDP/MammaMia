from mamma_mia import Mission
from dataclasses import dataclass
import uuid

@dataclass
class Campaign:
    name: str
    description: str
    missions: dict[str, Mission]
    id: uuid.UUID = uuid.uuid4()

    def run(self):
        for mission in self.missions.values():
            mission.fly()

    def visualise(self):
        for mission in self.missions.values():
            for var in mission.world.matched_worlds.items():
                mission.show_reality(parameter=str(var))