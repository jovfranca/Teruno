from dataclasses import dataclass

from .genetics import Genome


@dataclass
class Individual:
    id: str
    age: int
    energy: float
    food: float
    genome: Genome
    generation: int = 0
    alive: bool = True
