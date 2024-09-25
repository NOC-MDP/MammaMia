from mamma_mia.mission import Mission
from dataclasses import dataclass,field
import uuid
from loguru import logger

@dataclass
class Campaign:
    name: str
    description: str
    missions: dict[str, Mission] = field(init=False, default_factory=dict)
    id: uuid.UUID = uuid.uuid4()
    def __post_init__(self):
        logger.success(f"Campaign {self.name} created")

    def add_mission(self,mission:Mission) -> ():
        logger.info(f"adding {mission.name} to {self.name}")
        self.missions[mission.name] = mission
        logger.success(f"successfully added {mission.name} to {self.name}")

    def run(self):
        logger.info(f"running {self.name}")
        for mission in self.missions.values():
            logger.info(f"flying {mission.name}")
            mission.fly()
        logger.success(f"{self.name} finished successfully")

    def visualise(self):
        for mission in self.missions.values():
            for var in mission.world.matched_worlds.items():
                mission.show_reality(parameter=str(var))

    def export(self):
        raise NotImplementedError