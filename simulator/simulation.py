from collections import Counter
import math
import random
import statistics
from typing import TypedDict

from .config import SimulationConfig
from .genetics import Genome, TRAIT_NAMES
from .individual import Individual
from .neural_network import choose_action


class SimulationSummary(TypedDict):
    tick: int
    population: int
    births: int
    deaths: int
    generations: int
    food: float
    food_per_capita: float
    environmental_resource: float
    average_energy: float
    average_age: float
    average_traits: dict[str, float]
    history: tuple[int, ...]
    last_actions: dict[str, int]
    food_produced: float


class Simulation:
    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or SimulationConfig()
        self.rng = random.Random(self.config.seed)
        self.next_id = 1
        self.population = []
        initial_genomes = Genome.stratified_population(self.config.initial_population,
                                                       self.rng)
        for genome in initial_genomes:
            person = self._new_individual(genome, 0)
            person.age = self.rng.randrange(min(self.config.max_age, 10))
            self.population.append(person)
        self.initial_population = len(self.population)
        self.initial_population_snapshot = self._population_snapshot(self.living)
        self.last_nonempty_population_snapshot = self.initial_population_snapshot
        self.births = 0
        self.deaths = 0
        self.generations_reached = 0
        self.food_produced = 0.0
        self.environmental_resource = self.config.resource_capacity
        self.tick = 0
        self.food_consumed = 0.0
        self.history = [len(self.living)]
        self.last_actions: Counter[str] = Counter()

    def _new_individual(self, genome: Genome, generation: int) -> Individual:
        person = Individual(f"person-{self.next_id:06d}", 0, 70.0, 4.0, genome, generation)
        self.next_id += 1
        return person

    @property
    def living(self) -> list[Individual]:
        return [person for person in self.population if person.alive]

    def _inputs(self, person: Individual) -> tuple[float, ...]:
        return (min(1.0, person.energy / 100.0),
                min(1.0, person.food / 20.0),
                min(1.0, person.age / self.config.max_age),
                self.environmental_resource / self.config.resource_capacity)

    def step(self) -> None:
        self.tick += 1
        actions: Counter[str] = Counter()
        actors = tuple(self.living)
        resource_fraction = self.environmental_resource / self.config.resource_capacity
        resource_used = 0.0
        for person in actors:
            if not person.alive:
                continue
            action = choose_action(person.genome, self._inputs(person))
            actions[action] += 1
            if action == "WORK":
                strength, _, _, efficiency = person.genome.traits
                produced = 3.0 * efficiency * (0.5 + strength) * resource_fraction
                resource_used += produced
                person.food += produced
                self.food_produced += produced
                person.energy -= min(6.0, 1.0 + produced)
            elif action == "EAT":
                consumed = min(person.food, 2.0)
                person.food -= consumed
                self.food_consumed += consumed
                person.energy += consumed * 12.0
            else:
                self._reproduce(person)
                person.energy -= 2.0

            person.age += 1
            person.energy -= 1.5 + person.genome.traits[1]
            if person.food <= 0.0:
                person.energy -= 4.0
            if person.energy <= 0.0 or person.age >= self.config.max_age:
                person.alive = False
                self.deaths += 1

        self.environmental_resource = min(
            self.config.resource_capacity,
            max(0.0, self.environmental_resource - resource_used)
            + self.config.resource_regeneration)
        self.last_actions = actions
        self.history.append(len(self.living))
        if self.living:
            self.last_nonempty_population_snapshot = self._population_snapshot(self.living)

    @property
    def extinct(self) -> bool:
        return not self.living

    def _reproduce(self, parent: Individual) -> None:
        if (parent.age < 3 or parent.energy < 35.0 or parent.food < 3.0
                or len(self.living) >= self.config.max_population):
            return
        eligible = [person for person in self.living
                    if person.id != parent.id and person.age >= 3
                    and person.energy >= 25.0]
        if not eligible:
            return
        partner = min(eligible, key=lambda person: person.id)
        fertility = (parent.genome.traits[2] + partner.genome.traits[2]) / 2.0
        food_availability = min(1.0, self.total_food / max(1.0, len(self.living) * 3.0))
        fertility *= food_availability
        if self.rng.random() > fertility:
            return
        genome = Genome.inherit(parent.genome, partner.genome, self.rng,
                                self.config.mutation_rate)
        parent.food -= 3.0
        parent.energy -= 12.0
        self.population.append(self._new_individual(
            genome, max(parent.generation, partner.generation) + 1))
        self.generations_reached = max(self.generations_reached,
                                       self.population[-1].generation)
        self.births += 1

    @property
    def total_food(self) -> float:
        return sum(person.food for person in self.living)

    def average_traits(self) -> dict[str, float]:
        people = self.living
        if not people:
            return {name: 0.0 for name in TRAIT_NAMES}
        return {name: sum(person.genome.traits[index] for person in people) / len(people)
                for index, name in enumerate(TRAIT_NAMES)}

    @staticmethod
    def _distribution(values: list[float]) -> dict[str, float]:
        if not values:
            return {key: 0.0 for key in
                    ("min", "average", "median", "max", "stdev", "p25", "p75")}
        ordered = sorted(values)

        def percentile(fraction: float) -> float:
            position = fraction * (len(ordered) - 1)
            lower = math.floor(position)
            upper = math.ceil(position)
            return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

        return {"min": ordered[0], "average": statistics.fmean(ordered),
                "median": statistics.median(ordered), "max": ordered[-1],
                "stdev": statistics.pstdev(ordered), "p25": percentile(0.25),
                "p75": percentile(0.75)}

    @classmethod
    def _population_snapshot(cls, people: list[Individual]) -> dict[str, object]:
        trait_stats = {
            name: cls._distribution([person.genome.traits[index] for person in people])
            for index, name in enumerate(TRAIT_NAMES)
        }
        policy_stats: dict[str, object] = {}
        for action_index, action in enumerate(("WORK", "EAT", "REPRODUCE")):
            policy_stats[action] = {
                "weights": {
                    f"input_{input_index}": cls._distribution(
                        [person.genome.weights[action_index][input_index] for person in people])
                    for input_index in range(4)
                },
                "bias": cls._distribution(
                    [person.genome.biases[action_index] for person in people]),
            }
        snapshot: dict[str, object] = {
            "population": len(people), "traits": trait_stats,
            "policy": policy_stats,
        }
        if len(people) <= 10:
            snapshot["individuals"] = [
                {"id": person.id, "generation": person.generation, "age": person.age,
                 "energy": person.energy, "food": person.food,
                 "traits": dict(zip(TRAIT_NAMES, person.genome.traits))}
                for person in people
            ]
        return snapshot

    def summary(self) -> SimulationSummary:
        people = self.living
        return {
            "tick": self.tick,
            "population": len(people),
            "births": self.births,
            "deaths": self.deaths,
            "generations": self.generations_reached,
            "food": self.total_food,
            "food_per_capita": self.total_food / len(people) if people else 0.0,
            "environmental_resource": self.environmental_resource,
            "average_energy": sum(p.energy for p in people) / len(people) if people else 0.0,
            "average_age": sum(p.age for p in people) / len(people) if people else 0.0,
            "average_traits": self.average_traits(),
            "trait_statistics": self._population_snapshot(people)["traits"],
            "policy_statistics": self._population_snapshot(people)["policy"],
            "initial_population_snapshot": self.initial_population_snapshot,
            "last_nonempty_population_snapshot": self.last_nonempty_population_snapshot,
            "history": tuple(self.history),
            "last_actions": dict(self.last_actions),
            "food_produced": self.food_produced,
            "food_consumed": self.food_consumed,
        }

    def run(self) -> dict[str, object]:
        for _ in range(self.config.ticks):
            if self.extinct:
                break
            self.step()
        return self.summary()
