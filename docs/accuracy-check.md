# Accuracy check

Back to the [README](../README.md). Paths below are relative to the repository root.


Small hand-labelled eval in `evals/` (details and tables: `evals/results.md`; rubric: `evals/RUBRIC.md`; run `python evals/run_eval.py --split dev --verdicts`). The 118 real precedents were labelled blind from the case text (one labeller, the same person who wrote the mapper), split 72 dev / 46 held-out. Mapper errors were inspected and fixed on dev only; the held-out set was scored once (logged in `evals/heldout_runs.log`).

| | Dev before | Dev after (tuned) | Held-out (once) |
|---|---|---|---|
| Clause mapping accuracy | 88.9% | 94.4% | 95.7% (95% CI 85.5-98.8, n=46) |
| India outcome tag accuracy | 75.0% | 100% | 95.0% (CI 76.4-99.1, n=20) |
| Verdict logic checks | | | 17/17 |

Limitations: ground truth is one person's reading, not independent experts; small samples (wide intervals); dev gains are fitted to dev and not evidence of generalisation; the held-out set is small and the precedents were keyword-selected, so accuracy on arbitrary cases would be lower; the mapper cannot answer "no clause"; the verdict checks only show the rules behave as written. The fixes changed 12 stored India outcome tags (the old tagger was wrong on about a quarter of dev awards).
