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

    def test_cli_accepts_resource_configuration(self) -> None:
        with patch("sys.argv", ["simulator", "--resource-capacity", "250",
                                "--resource-regeneration", "12", "--ticks", "0"]):
            constructed_configs = []
            def construct(config):
                constructed_configs.append(config)
                return Simulation(config)
            with patch("simulator.cli.Simulation", side_effect=construct):
                with redirect_stdout(StringIO()):
                    cli_main()
                self.assertEqual(constructed_configs[0].resource_capacity, 250.0)
                self.assertEqual(constructed_configs[0].resource_regeneration, 12.0)

    def test_initial_ages_vary_deterministically(self) -> None:
        config = SimulationConfig(seed=17, initial_population=20, ticks=0)
        first = Simulation(config)
        second = Simulation(config)
        first_ages = [person.age for person in first.living]
        self.assertEqual(first_ages, [person.age for person in second.living])
        self.assertGreater(len(set(first_ages)), 1)
        self.assertTrue(all(0 <= age < 10 for age in first_ages))

    def test_newborn_starts_at_age_zero(self) -> None:
        simulation = Simulation(SimulationConfig(seed=11, initial_population=3, ticks=0))
        parent, partner, _ = simulation.living
        for person in (parent, partner):
            person.age = 4
            person.energy = 80.0
            person.food = 10.0
            person.genome = Genome((0.8, 0.5, 1.0, 0.8), ((0.0,) * 4,) * 3,
                                   (0.0, 0.0, 1.0))
        simulation._reproduce(parent)
        self.assertEqual(simulation.population[-1].age, 0)

    def test_run_stops_on_extinction_and_keeps_extinction_tick(self) -> None:
        simulation = Simulation(SimulationConfig(initial_population=1, ticks=20, max_age=1))
        result = simulation.run()
        self.assertEqual(result["population"], 0)
        self.assertEqual(result["tick"], 1)
        self.assertEqual(len(result["history"]), 2)

    def test_same_seed_and_configuration_produce_same_result(self) -> None:
        config = SimulationConfig(seed=42, initial_population=12, ticks=80)
        first = Simulation(config).run()
        second = Simulation(config).run()
        self.assertEqual(first, second)

    def test_initial_genomes_are_seeded_and_population_stratified(self) -> None:
        config = SimulationConfig(seed=42, initial_population=100, ticks=0)
        first = Simulation(config)
        second = Simulation(config)
        genomes_a = [person.genome for person in first.living]
        genomes_b = [person.genome for person in second.living]
        self.assertEqual(genomes_a, genomes_b)
        for trait_index in range(4):
            values = [genome.traits[trait_index] for genome in genomes_a]
            self.assertGreater(min(values), 0.0)
            self.assertLess(max(values), 1.0)
            self.assertGreater(max(values) - min(values), 0.95)
        for action in range(3):
            for input_index in range(4):
                values = [genome.weights[action][input_index] for genome in genomes_a]
                self.assertGreater(max(values) - min(values), 3.8)
            biases = [genome.biases[action] for genome in genomes_a]
            self.assertGreater(max(biases) - min(biases), 3.8)

    def test_initial_space_filling_is_deterministic_for_same_seed_and_size(self) -> None:
        import random
        first = Genome.stratified_population(12, random.Random(19))
        second = Genome.stratified_population(12, random.Random(19))
        self.assertEqual(first, second)

    def test_trait_statistics_are_correct(self) -> None:
        stats = Simulation._distribution([0.0, 0.25, 0.5, 0.75, 1.0])
        self.assertEqual(stats["min"], 0.0)
        self.assertEqual(stats["max"], 1.0)
        self.assertEqual(stats["average"], 0.5)
        self.assertEqual(stats["median"], 0.5)
        self.assertEqual(stats["p25"], 0.25)
        self.assertEqual(stats["p75"], 0.75)

    def test_policy_aggregate_statistics_are_deterministic(self) -> None:
        config = SimulationConfig(seed=31, initial_population=12, ticks=0)
        first = Simulation(config).summary()["policy_statistics"]
        second = Simulation(config).summary()["policy_statistics"]
        self.assertEqual(first, second)

    def test_last_nonempty_statistics_survive_extinction(self) -> None:
        simulation = Simulation(SimulationConfig(seed=4, initial_population=4,
                                                 ticks=0, max_age=1))
        for person in simulation.living:
            person.age = 0
        simulation.step()
        summary = simulation.summary()
        snapshot = summary["last_nonempty_population_snapshot"]
        self.assertEqual(summary["population"], 0)
        self.assertGreater(snapshot["population"], 0)
        self.assertIn("work_efficiency", snapshot["traits"])
        self.assertIn("WORK", snapshot["policy"])
        self.assertIn("individuals", snapshot)

    def test_policy_receives_environmental_resource_availability(self) -> None:
        simulation = Simulation(SimulationConfig(initial_population=1, ticks=0,
                                                 resource_capacity=100.0))
        person = simulation.living[0]
        simulation.environmental_resource = 25.0
        self.assertEqual(simulation._inputs(person)[-1], 0.25)

    def test_starter_policy_work_score_falls_when_resources_are_scarce(self) -> None:
        genome = Genome((0.5,) * 4, ((0.0, 0.0, 0.0, 1.5),
                                     (0.0,) * 4, (0.0, 0.0, 0.0, -1.0)),
                        (0.0, 0.0, -1.0))
        simulation = Simulation(SimulationConfig(initial_population=1, ticks=0))
        person = simulation.living[0]
        abundant_resource = simulation._inputs(person)[-1]
        simulation.environmental_resource = 0.0
        scarce_resource = simulation._inputs(person)[-1]
        self.assertGreater(genome.weights[0][-1] * abundant_resource,
                           genome.weights[0][-1] * scarce_resource)

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
                                                 resource_capacity=40.0,
                                                 resource_regeneration=10.0))
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
