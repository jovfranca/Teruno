import random
import unittest

from simulator import Simulation, SimulationConfig
from simulator.genetics import Genome


class SimulationTests(unittest.TestCase):
    def test_same_seed_and_configuration_produce_same_result(self) -> None:
        config = SimulationConfig(seed=42, initial_population=12, ticks=80)
        first = Simulation(config).run()
        second = Simulation(config).run()
        self.assertEqual(first, second)

    def test_different_seeds_produce_different_initial_populations(self) -> None:
        first = Simulation(SimulationConfig(seed=1, initial_population=8, ticks=0))
        second = Simulation(SimulationConfig(seed=2, initial_population=8, ticks=0))
        self.assertNotEqual([p.genome for p in first.living], [p.genome for p in second.living])

    def test_inheritance_combines_parents_and_mutates_deterministically(self) -> None:
        first = Genome((0.2,) * 4, ((0.2,) * 4,) * 3, (0.2,) * 3)
        second = Genome((0.8,) * 4, ((0.8,) * 4,) * 3, (0.8,) * 3)
        child = Genome.inherit(first, second, random.Random(7), 0.0)
        self.assertEqual(child.traits, (0.5,) * 4)
        self.assertEqual(child.weights, ((0.5,) * 4,) * 3)
        mutated_a = Genome.inherit(first, second, random.Random(7), 1.0)
        mutated_b = Genome.inherit(first, second, random.Random(7), 1.0)
        self.assertEqual(mutated_a, mutated_b)
        self.assertNotEqual(mutated_a, child)

    def test_reproduction_creates_inheriting_child_and_death_is_counted(self) -> None:
        simulation = Simulation(SimulationConfig(seed=11, initial_population=3,
                                                 ticks=0, max_age=10))
        parent, partner, victim = simulation.living
        for person in (parent, partner):
            person.age = 4
            person.energy = 80.0
            person.food = 10.0
            person.genome = Genome((0.8, 0.5, 1.0, 0.8), ((0.0,) * 4,) * 3, (0.0, 0.0, 1.0))
        simulation._reproduce(parent)
        self.assertEqual(simulation.births, 1)
        self.assertEqual(len(simulation.population), 4)
        self.assertEqual(simulation.population[-1].generation, 1)
        self.assertEqual(simulation.summary()["generations"], 1)
        victim.age = 9
        # A forced EAT policy keeps both parents alive; the victim ages out on this tick.
        victim.genome = Genome(victim.genome.traits,
                               ((0.0,) * 4, (0.0,) * 4, (0.0,) * 4),
                               (-1.0, 1.0, -1.0))
        simulation.step()
        self.assertFalse(victim.alive)
        self.assertEqual(simulation.deaths, 1)


if __name__ == "__main__":
    unittest.main()
