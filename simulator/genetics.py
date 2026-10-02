from dataclasses import dataclass
import random


TRAIT_NAMES = ("strength", "metabolism", "fertility", "work_efficiency")
INPUT_COUNT = 4
ACTION_NAMES = ("WORK", "EAT", "REPRODUCE")


@dataclass(frozen=True)
class Genome:
    traits: tuple[float, ...]
    # One four-input linear unit (weights and bias) for each action.
    weights: tuple[tuple[float, ...], ...]
    biases: tuple[float, ...]

    @classmethod
    def random(cls, rng: random.Random) -> "Genome":
        # Small seeded variation around a resource-aware starter policy keeps
        # the initial population viable while leaving room for evolution.
        starter_weights = ((0.0, -1.5, 0.0, 1.5),
                           (-3.0, 2.0, 0.0, 0.0),
                           (0.8, 0.5, 0.0, -1.0))
        starter_biases = (0.0, -0.2, -1.0)
        return cls(
            traits=tuple(rng.random() for _ in TRAIT_NAMES),
            weights=tuple(
                tuple(weight + rng.uniform(-0.15, 0.15) for weight in row)
                for row in starter_weights
            ),
            biases=tuple(bias + rng.uniform(-0.1, 0.1) for bias in starter_biases),
        )

    @classmethod
    def inherit(cls, first: "Genome", second: "Genome", rng: random.Random,
                mutation_rate: float) -> "Genome":
        def inherit_value(a: float, b: float, low: float, high: float) -> float:
            value = (a + b) / 2.0
            if rng.random() < mutation_rate:
                value += rng.uniform(-0.1, 0.1)
            return min(high, max(low, value))

        traits = tuple(inherit_value(a, b, 0.0, 1.0)
                       for a, b in zip(first.traits, second.traits))
        weights = tuple(
            tuple(inherit_value(a, b, -2.0, 2.0)
                  for a, b in zip(row_a, row_b))
            for row_a, row_b in zip(first.weights, second.weights)
        )
        biases = tuple(inherit_value(a, b, -2.0, 2.0)
                       for a, b in zip(first.biases, second.biases))
        return cls(traits, weights, biases)
