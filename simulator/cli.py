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
    parser.add_argument("--resource-capacity", type=float, default=1000.0)
    parser.add_argument("--resource-regeneration", type=float, default=50.0)
    args = parser.parse_args()
    config = SimulationConfig(seed=args.seed, initial_population=args.population,
                              ticks=args.ticks, mutation_rate=args.mutation_rate,
                              max_population=args.max_population,
                              report_every=args.report_every,
                              resource_capacity=args.resource_capacity,
                              resource_regeneration=args.resource_regeneration)
    simulation = Simulation(config)
    print(f"Civilization Simulation | seed {config.seed} | initial population {len(simulation.living)}")
    for _ in range(config.ticks):
        if simulation.extinct:
            break
        simulation.step()
        if simulation.tick % config.report_every == 0 or simulation.tick == config.ticks:
            _print_report(simulation)
        if simulation.extinct:
            print(f"Population extinct at tick {simulation.tick}.")
            if simulation.tick % config.report_every != 0:
                _print_report(simulation)
            break
    result = simulation.summary()
    print("\nFinal summary")
    print(f"Initial population: {simulation.initial_population}")
    print(f"Final population:   {result['population']}")
    if simulation.extinct:
        print(f"Extinction tick:    {result['tick']}")
    print(f"Births:             {result['births']}")
    print(f"Deaths:             {result['deaths']}")
    print(f"Generations:        {result['generations']}")
    print(f"Food produced:      {result['food_produced']:.1f}")
    print(f"Food consumed:      {result['food_consumed']:.1f}")
    print(f"Food per capita:    {result['food_per_capita']:.1f}")
    print(f"Environmental resource: {result['environmental_resource']:.1f} / {config.resource_capacity:.1f}")
    print("Trait distributions (initial -> final; avg [min, max], sd)")
    initial_traits = result["initial_population_snapshot"]["traits"]
    final_snapshot = (result["last_nonempty_population_snapshot"]
                      if result["population"] == 0 else
                      {"traits": result["trait_statistics"],
                       "policy": result["policy_statistics"]})
    final_traits = final_snapshot["traits"]
    for name in initial_traits:
        start = initial_traits[name]
        end = final_traits[name]
        print(f"  {name:16} {start['average']:.3f} [{start['min']:.2f}, {start['max']:.2f}], "
              f"sd {start['stdev']:.2f} -> {end['average']:.3f} "
              f"[{end['min']:.2f}, {end['max']:.2f}], sd {end['stdev']:.2f}")
    print("Policy parameter average weights by input and bias (initial -> final)")
    initial_policy = result["initial_population_snapshot"]["policy"]
    for action, values in final_snapshot["policy"].items():
        start_values = initial_policy[action]
        weights = ", ".join(
            f"{start_values['weights'][key]['average']:+.2f}->{stats['average']:+.2f}"
            for key, stats in values["weights"].items())
        print(f"  {action:10} weights [{weights}] bias "
              f"{start_values['bias']['average']:+.2f}->{values['bias']['average']:+.2f}")
    if "individuals" in final_snapshot:
        print("Last living individuals")
        for person in final_snapshot["individuals"]:
            traits = ", ".join(f"{name}={value:.2f}"
                                for name, value in person["traits"].items())
            print(f"  {person['id']} gen={person['generation']} age={person['age']} "
                  f"energy={person['energy']:.1f} food={person['food']:.1f} {traits}")
    _print_population_chart(result["history"])
