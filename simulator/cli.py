import argparse

from .config import SimulationConfig
from .simulation import Simulation


def _print_report(simulation: Simulation) -> None:
    report = simulation.summary()
    print(f"Tick {report['tick']:>4} | population {report['population']:>4} | "
          f"resource {report['environmental_resource']:>7.1f} | "
          f"food {report['food']:>8.1f} ({report['food_per_capita']:.1f}/person) | "
          f"births {report['births']:>4} | "
          f"deaths {report['deaths']:>4}")
    actions = report["last_actions"]
    print("  Actions: " + ", ".join(
        f"{name} {count}" for name, count in sorted(actions.items())))


def _print_population_chart(history: tuple[int, ...]) -> None:
    samples = history[::max(1, len(history) // 40)]
    peak = max(samples, default=0)
    if peak == 0:
        print("Population history: (population extinct)")
        return
    print("Population history:")
    for level in range(4, 0, -1):
        threshold = peak * level / 4
        print(f"{threshold:5.0f} | " + " ".join("#" if value >= threshold else " "
                                                  for value in samples))


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic civilization simulator")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--population", type=int, default=30)
    parser.add_argument("--ticks", type=int, default=500)
    parser.add_argument("--mutation-rate", type=float, default=0.05)
    parser.add_argument("--max-population", type=int, default=500,
                        help="computational safety population limit (default: 500)")
    parser.add_argument("--report-every", type=int, default=50)
    args = parser.parse_args()
    config = SimulationConfig(seed=args.seed, initial_population=args.population,
                              ticks=args.ticks, mutation_rate=args.mutation_rate,
                              max_population=args.max_population,
                              report_every=args.report_every)
    simulation = Simulation(config)
    print(f"Civilization Simulation | seed {config.seed} | initial population {len(simulation.living)}")
    for _ in range(config.ticks):
        simulation.step()
        if simulation.tick % config.report_every == 0 or simulation.tick == config.ticks:
            _print_report(simulation)
    result = simulation.summary()
    print("\nFinal summary")
    print(f"Initial population: {simulation.initial_population}")
    print(f"Final population:   {result['population']}")
    print(f"Births:             {result['births']}")
    print(f"Deaths:             {result['deaths']}")
    print(f"Generations:        {result['generations']}")
    print(f"Food produced:      {result['food_produced']:.1f}")
    print(f"Food consumed:      {result['food_consumed']:.1f}")
    print(f"Food per capita:    {result['food_per_capita']:.1f}")
    print(f"Environmental resource: {result['environmental_resource']:.1f} / {config.resource_capacity:.1f}")
    print("Average traits (beginning -> end)")
    for name, start in simulation.initial_traits.items():
        print(f"  {name:16} {start:.3f} -> {result['average_traits'][name]:.3f}")
    _print_population_chart(result["history"])
