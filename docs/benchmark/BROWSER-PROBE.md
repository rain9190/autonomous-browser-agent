# Browser feasibility probe

Before expanding the MiniWoB task list, this script checked whether candidate tasks loaded
and exposed usable controls. It reads the initial page; it doesn't choose or execute actions.

```bash
python scripts/probe_benchmark_tasks.py --seed 61
```

For a smaller check:

```bash
python scripts/probe_benchmark_tasks.py --seed 61 --tasks click-link choose-list
```

The probe accepts development seeds 61/67 only. Each task has a 45-second worker deadline.
Reports go to a new `results/feasibility-*` folder and include accessibility roles, visible
DOM controls, observation size and truncation flags. No model calls are made.

Loading a task isn't the same as solving it. The findings helped identify missing selection,
tab and link support. [Recorded results](FEASIBILITY-RESULTS.md)
