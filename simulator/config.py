from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    """Simulation settings; max_population is a computational safety limit.

    It is not an environmental carrying capacity and is not derived from
    available resources.
    """

    seed: int = 42
    initial_population: int = 30
    ticks: int = 500
    mutation_rate: float = 0.05
    max_population: int = 500  # Computational safety limit, not carrying capacity.
    max_age: int = 80
    report_every: int = 50
    resource_capacity: float = 1000.0
    resource_regeneration: float = 20.0

    def __post_init__(self) -> None:
        if self.initial_population < 1:
            raise ValueError("initial_population must be at least 1")
        if self.ticks < 0:
            raise ValueError("ticks cannot be negative")
        if not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("mutation_rate must be between 0 and 1")
        if self.max_population < self.initial_population:
            raise ValueError("max_population cannot be smaller than initial_population")
        if self.max_age < 1 or self.report_every < 1:
            raise ValueError("max_age and report_every must be at least 1")
        if self.resource_capacity <= 0.0:
            raise ValueError("resource_capacity must be greater than 0")
        if not 0.0 <= self.resource_regeneration <= self.resource_capacity:
            raise ValueError("resource_regeneration must be between 0 and resource_capacity")
