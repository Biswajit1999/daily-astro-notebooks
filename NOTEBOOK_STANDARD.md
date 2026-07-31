# Notebook analysis standard

The goal is a small, reproducible scientific investigation rather than a collection of plots. A notebook is marked **dense** in the dashboard only when it meets the checks below.

## Required structure

1. **Question** — one answerable scientific question and a short reason it matters.
2. **Data trail** — archive, table or product identifier, query, access date, units, and citation.
3. **Quality cuts** — every filter is visible in code and the sample size is printed after each important cut.
4. **Exploration** — plots show the data distribution before the main measurement is made.
5. **Measurement** — the notebook reports at least one numerical result with units.
6. **Uncertainty** — bootstrap, fit covariance, measurement errors, or another suitable uncertainty estimate.
7. **Stress test** — change a threshold, selection, model, or binning choice and show whether the conclusion survives.
8. **Physical reading** — explain what the result means without claiming more than the data support.
9. **Published comparison** — compare with an archive paper or peer-reviewed result and link the source.
10. **Limits and next step** — name the strongest limitation and a concrete follow-up analysis.

## Files in each dense analysis

- `notebook.ipynb` with executed outputs
- `README.md` with the question, result, interpretation, limits, and references
- `result.json` for the dashboard
- small input tables or archive products needed for repeatable offline checks
- exported figures used in the README and dashboard

## Interpretation rules

- A correlation is not described as a cause.
- A selected sample is not presented as the full sky or full archive.
- Statistical uncertainty and known systematic uncertainty are kept separate.
- Archive measurements retain their original units until an explicit conversion is shown.
- Failed or inconclusive tests remain useful and should be reported honestly.

## Review checklist

Before merging, restart and run every cell, confirm there are no hidden errors, verify that figure labels include units, check that the README agrees with the printed results, and make sure every external data product and paper is cited.
