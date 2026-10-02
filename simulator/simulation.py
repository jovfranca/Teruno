from collections import Counter
import random
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
        self.population = [self._new_individual(Genome.random(self.rng), 0)
                           for _ in range(self.config.initial_population)]
        self.initial_traits = self.average_traits()
        self.initial_population = len(self.population)
        self.births = 0
        self.deaths = 0
        self.generations_reached = 0
        self.food_produced = 0.0
        self.tick = 0
        self.history = [len(self.living)]
        self.last_actions: Counter[str] = Counter()

    def _new_individual(self, genome: Genome, generation: int) -> Individual:
        person = Individual(f"person-{self.next_id:06d}", 0, 70.0, 4.0, genome, generation)
        self.next_id += 1
        return person

    @property
    def living(self) -> list[Individual]:
        return [person for person in self.population if person.alive]

    def _inputs(self, person: Individual, global_food: float,
                population_size: int) -> tuple[float, ...]:
        return (min(1.0, person.energy / 100.0),
                min(1.0, person.food / 20.0),
                min(1.0, person.age / self.config.max_age),
                min(1.0, global_food / max(1.0, population_size * 10.0)))

    def step(self) -> None:
        self.tick += 1
        actions: Counter[str] = Counter()
        actors = tuple(self.living)
        global_food = sum(person.food for person in actors)
        for person in actors:
            if not person.alive:
                continue
            action = choose_action(person.genome,
                                   self._inputs(person, global_food, len(actors)))
            actions[action] += 1
            if action == "WORK":
                strength, _, _, efficiency = person.genome.traits
                produced = 3.0 * efficiency * (0.5 + strength)
                person.food += produced
                self.food_produced += produced
                person.energy -= 6.0
            elif action == "EAT":
                consumed = min(person.food, 2.0)
                person.food -= consumed
                person.energy += consumed * 12.0
            else:
                self._reproduce(person)
                person.energy -= 2.0

            person.age += 1
            person.energy -= 1.5 + person.genome.traits[1]
            if person.energy <= 0.0 or person.age >= self.config.max_age:
                person.alive = False
                self.deaths += 1

        self.last_actions = actions
        self.history.append(len(self.living))

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

    def summary(self) -> SimulationSummary:
        people = self.living
        return {
            "tick": self.tick,
            "population": len(people),
            "births": self.births,
            "deaths": self.deaths,
            "generations": self.generations_reached,
            "food": self.total_food,
            "average_energy": sum(p.energy for p in people) / len(people) if people else 0.0,
            "average_age": sum(p.age for p in people) / len(people) if people else 0.0,
            "average_traits": self.average_traits(),
            "history": tuple(self.history),
            "last_actions": dict(self.last_actions),
            "food_produced": self.food_produced,
        }

    def run(self) -> dict[str, object]:
        for _ in range(self.config.ticks):
            self.step()
        return self.summary()
