from mamma_mia.mission import Mission
from dataclasses import dataclass,field
import uuid

@dataclass
class Campaign:
    name: str
    description: str
    missions: dict[str, Mission] = field(init=False, default_factory=dict)
    id: uuid.UUID = uuid.uuid4()

    def add_mission(self,mission:Mission) -> ():
        self.missions[mission.name] = mission

    def run(self):
        for mission in self.missions.values():
            mission.fly()

    def visualise(self):
        for mission in self.missions.values():
            for var in mission.world.matched_worlds.items():
                mission.show_reality(parameter=str(var))