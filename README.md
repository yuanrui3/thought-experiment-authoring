# Thought-experiment authoring (pilot)

**Status, 15 November 2026: paused, waiting for human participants.** The model-panel pilot is complete. The human survey is built and tested but nobody has taken it. To resume, follow `docs/human-survey.md`.

A small benchmark: an author model gets one philosophical factor, writes a pair of
short scenarios that differ only in that factor, and predicts how readers will judge
them. A blind panel rates the scenarios, each judge seeing one version, and the pair
is scored on whether ratings split as predicted, on confounds, on originality and on
comprehension.

This release is a pilot of the pipeline. All authors and judges are Claude models. No human has judged the pairs yet, so the results show how a model panel responds, not how people do; a human run is the planned next step.

## Files

| File | What it is |
|---|---|
| `results.html` | Results page (open in a browser). |
| `METHODS.md` | One-page methods note: judgment calls, limitations, next steps. |
| `docs/prior-art.md` | Prior-art check and verdict. |
| `docs/control-references.md` | Check of the classic controls' references against their source papers. |
| `docs/human-survey.md` | How to run the human survey, and the analysis plan fixed in advance. |
| `survey/survey.html` | The human survey as a single file. `survey/survey_page.html` is the same page for publishing. |
| `compare_panels.py` | Compares the human panel with the model panel once human data exists. |
| `reports/Mathematical analysis of the benchmark.md` | What the pilot data imply about factor choice, the prediction score, human sample sizes, the calibration bar and the survey design. Rebuilt by `pipeline/math_analysis.py`. |
| `reports/Calibration on public human data.md` | The model panel run on two public datasets with human ratings (OffTheRails, MoCa) and scored with the pilot's own gap rule: how often its verdicts match people's, factor by factor. Numbers in `reports/calibration_numbers.json`, rebuilt by `pipeline/calibration/analyse.py`. |
| `reports/Statistical methods for vignette benchmarks.md` | Review of recent statistics (2023–2026) that could fix the problems the analysis found, with each citation's verification status. |
| `vignettes.json` | All pairs, questions, predictions, authors, control references. |
| `judgments.csv` | One row per judge and scenario. |
| `audits.csv` | One row per auditor and pair (confounds, originality). |
| `score.py` | Recomputes every number and rebuilds `results.html`. |
| `report.py` | Page builder, called by `score.py`. |
| `commentary.json` | Hand-written findings and diagnoses shown on the page. |
| `annotations.json` | Hand-made flags for pairs that share a setting; they change no score. |
| `out/` | `pair_scores.csv`, `author_summary.csv`, `results.json`. |
| `pipeline/` | How the data was produced: author brief, controls, batch randomisation, panel scripts, ingestion, raw outputs; the survey generator, its private key (`survey_manifest.json`) and `ingest_survey.py`. `pipeline/calibration/` holds the calibration run: batch and recognition builders, the panel's answers, judge provenance and the analysis. |

## Rerun

```bash
python3 score.py
```

Python 3.9 or later, standard library only. Options: `--run` (which `run_id` to
score), `--boot` (bootstrap resamples), `--seed`.

## Adding judges or authors

- **More judges (another vendor's model, or people):** append rows to `judgments.csv`.
  Set `judge_type` (`llm` or `human`), `judge_vendor`, `judge_model`, a `judge_group`
  (the stratum that gets equal weight, for example `openai/<model>` or
  `human/prolific-us`) and a unique `judge_id` per rater. A judge must never see both
  versions of a pair; `score.py` checks this.
- **More authors:** add pairs to `vignettes.json` with a new `author` block and
  collect judgments for them.
- **More auditors:** append rows to `audits.csv`.

## Licence

MIT. See `LICENSE`. It covers the code, the data files and the documentation in this repository.
