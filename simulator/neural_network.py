import math

from .genetics import ACTION_NAMES, Genome


def choose_action(genome: Genome, inputs: tuple[float, ...]) -> str:
    """Choose the highest scoring action from the individual's tiny policy net."""
    scores = tuple(
        math.tanh(sum(weight * value for weight, value in zip(row, inputs)) + bias)
        for row, bias in zip(genome.weights, genome.biases)
    )
    return ACTION_NAMES[max(range(len(scores)), key=scores.__getitem__)]
