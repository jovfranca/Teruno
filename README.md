# Teruno

A deterministic, terminal based civilization simulation written in Python.

## Requirements

- Python 3.10 or newer
- No third-party packages are required

## Run the simulation

Open a terminal in the project directory (the directory containing this README), then run:

```powershell
python -m simulator
```

The simulator prints periodic reports and a final summary. To see all available options:

```powershell
python -m simulator --help
```

Example with custom settings:

```powershell
python -m simulator --seed 7 --population 40 --ticks 1000 --mutation-rate 0.08 --report-every 100 --max-population 600
```

Options:

| Option | Default | Description |
| --- | ---: | --- |
| `--seed` | `42` | Random seed for a reproducible run. |
| `--population` | `30` | Initial population. |
| `--ticks` | `500` | Number of simulation steps. |
| `--mutation-rate` | `0.05` | Mutation rate from `0` to `1`. |
| `--report-every` | `50` | Print a progress report every this many ticks. |
| `--max-population` | `500` | Computational safety limit on reproduction. |

Food production draws from a shared environmental resource. Work output falls as this resource is depleted, and it regenerates by 20 units per tick up to its capacity of 1000. Food scarcity lowers reproduction success and increases energy loss, which can lead to starvation deaths. The `--max-population` option remains a computational safety limit rather than an environmental carrying capacity.

## Run tests

```powershell
python -m unittest discover -s tests -v
```
