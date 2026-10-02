import random
from contextlib import redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from simulator import Simulation, SimulationConfig
from simulator.cli import main as cli_main
from simulator.genetics import Genome


class SimulationTests(unittest.TestCase):
    def test_max_population_defaults_to_500_safety_limit(self) -> None:
        self.assertEqual(SimulationConfig().max_population, 500)

    def test_cli_accepts_max_population(self) -> None:
        with patch("sys.argv", ["simulator", "--max-population", "40", "--ticks", "0"]):
            with redirect_stdout(StringIO()):
                cli_main()

    def test_same_seed_and_configuration_produce_same_result(self) -> None:
        config = SimulationConfig(seed=42, initial_population=12, ticks=80)
        first = Simulation(config).run()
        second = Simulation(config).run()
        self.assertEqual(first, second)

    def test_work_production_scales_with_resource_and_resource_regenerates(self) -> None:
        config = SimulationConfig(seed=8, initial_population=1, ticks=0,
                                  resource_capacity=100.0, resource_regeneration=1.0)
        abundant = Simulation(config)
        scarce = Simulation(config)
        for simulation in (abundant, scarce):
            person = simulation.living[0]
            person.genome = Genome((1.0, 0.0, 0.0, 1.0), ((0.0,) * 4,) * 3,
                                   (1.0, 0.0, 0.0))
        scarce.environmental_resource = 10.0
        with patch("simulator.simulation.choose_action", return_value="WORK"):
            abundant.step()
            scarce.step()
        self.assertLess(scarce.food_produced, abundant.food_produced)
        self.assertAlmostEqual(abundant.environmental_resource, 96.5)
        self.assertAlmostEqual(scarce.environmental_resource, 10.55)

    def test_food_scarcity_reduces_reproduction_and_increases_death_pressure(self) -> None:
        simulation = Simulation(SimulationConfig(seed=11, initial_population=2, ticks=0,
                                                 resource_regeneration=0.0))
        parent, partner = simulation.living
        for person in (parent, partner):
            person.age = 4
            person.energy = 80.0
            person.food = 0.0
            person.genome = Genome((0.8, 0.5, 1.0, 0.8), ((0.0,) * 4,) * 3,
                                   (0.0, 0.0, 1.0))
        simulation._reproduce(parent)
        self.assertEqual(simulation.births, 0)
        with patch("simulator.simulation.choose_action", return_value="EAT"):
            for _ in range(20):
                simulation.step()
        self.assertTrue(all(not person.alive for person in (parent, partner)))
        self.assertEqual(simulation.deaths, 2)

    def test_summary_exposes_resource_and_food_per_capita(self) -> None:
        simulation = Simulation(SimulationConfig(initial_population=2, ticks=0,
                                                 resource_capacity=40.0))
        report = simulation.summary()
        self.assertEqual(report["environmental_resource"], 40.0)
        self.assertEqual(report["food_per_capita"], 4.0)

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
