from dataclasses import dataclass
import random


TRAIT_NAMES = ("strength", "metabolism", "fertility", "work_efficiency")
INPUT_COUNT = 4
ACTION_NAMES = ("WORK", "EAT", "REPRODUCE")
WEIGHT_RANGE = (-2.0, 2.0)
TRAIT_RANGE = (0.0, 1.0)


def stratified_values(count: int, low: float, high: float,
                      rng: random.Random) -> list[float]:
    """Return one seeded sample from each equal-width stratum, shuffled."""
    values = [low + (index + rng.random()) * (high - low) / count
              for index in range(count)]
    rng.shuffle(values)
    return values


@dataclass(frozen=True)
class Genome:
    traits: tuple[float, ...]
    # One four-input linear unit (weights and bias) for each action.
    weights: tuple[tuple[float, ...], ...]
    biases: tuple[float, ...]

    @classmethod
    def random(cls, rng: random.Random) -> "Genome":
        """Create one broadly sampled genome (offspring use inherit instead)."""
        return cls(
            tuple(rng.uniform(*TRAIT_RANGE) for _ in TRAIT_NAMES),
            tuple(tuple(rng.uniform(*WEIGHT_RANGE) for _ in range(INPUT_COUNT))
                  for _ in ACTION_NAMES),
            tuple(rng.uniform(*WEIGHT_RANGE) for _ in ACTION_NAMES),
        )

    @classmethod
    def stratified_population(cls, count: int, rng: random.Random) -> list["Genome"]:
        """Space-fill every parameter dimension across an initial population."""
        dimensions = [stratified_values(count, *TRAIT_RANGE, rng)
                      for _ in TRAIT_NAMES]
        dimensions.extend(stratified_values(count, *WEIGHT_RANGE, rng)
                          for _ in range(len(ACTION_NAMES) * INPUT_COUNT))
        dimensions.extend(stratified_values(count, *WEIGHT_RANGE, rng)
                          for _ in ACTION_NAMES)
        genomes = []
        for member in range(count):
            traits = tuple(dimensions[index][member]
                           for index in range(len(TRAIT_NAMES)))
            offset = len(TRAIT_NAMES)
            weights = tuple(tuple(dimensions[offset + action * INPUT_COUNT + inp][member]
                                  for inp in range(INPUT_COUNT))
                            for action in range(len(ACTION_NAMES)))
            offset += len(ACTION_NAMES) * INPUT_COUNT
            biases = tuple(dimensions[offset + action][member]
                           for action in range(len(ACTION_NAMES)))
            genomes.append(cls(traits, weights, biases))
        return genomes

    @classmethod
    def inherit(cls, first: "Genome", second: "Genome", rng: random.Random,
                mutation_rate: float) -> "Genome":
        def inherit_value(a: float, b: float, low: float, high: float) -> float:
            value = (a + b) / 2.0
            if rng.random() < mutation_rate:
                value += rng.uniform(-0.1, 0.1)
            return min(high, max(low, value))

        traits = tuple(inherit_value(a, b, *TRAIT_RANGE)
                       for a, b in zip(first.traits, second.traits))
        weights = tuple(
            tuple(inherit_value(a, b, *WEIGHT_RANGE)
                  for a, b in zip(row_a, row_b))
            for row_a, row_b in zip(first.weights, second.weights)
        )
        biases = tuple(inherit_value(a, b, *WEIGHT_RANGE)
                       for a, b in zip(first.biases, second.biases))
        return cls(traits, weights, biases)
