# Thought-experiment authoring (pilot)

**Status, 15 November 2026.** The model-panel pilot is complete. The human study awaits
participants. This release archives the model-panel work and the human-study methods. The
human survey deployment files and scoring key are excluded.

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
| `docs/human-survey.md` | Human survey design and the analysis plan fixed in advance. |
| `compare_panels.py` | Compares the human panel with the model panel once human data exists. |
| `reports/Mathematical analysis of the benchmark.md` | What the pilot data imply about factor choice, the prediction score, human sample sizes, the calibration bar and the survey design. Rebuilding the survey section with `pipeline/math_analysis.py` requires the separate survey manifest. |
| `reports/Calibration on public human data.md` | The model panel run on two public datasets with human ratings (OffTheRails, MoCa) and scored with the pilot's own gap rule: how often its verdicts match people's, factor by factor; plus two Gemini models as a second vendor. Numbers in `reports/calibration_numbers.json` and `reports/calibration_numbers_other_panels.json`, rebuilt by `pipeline/calibration/analyse.py`. |
| `reports/Statistical methods for vignette benchmarks.md` | Review of recent statistics (2023–2026) that could fix the problems the analysis found, with each citation's verification status. |
| `vignettes.json` | All pairs, questions, predictions, authors, control references. |
| `judgments.csv` | One row per judge and scenario. |
| `audits.csv` | One row per auditor and pair (confounds, originality). |
| `score.py` | Recomputes every number and rebuilds `results.html`. |
| `report.py` | Page builder, called by `score.py`. |
| `commentary.json` | Hand-written findings and diagnoses shown on the page. |
| `annotations.json` | Hand-made flags for pairs that share a setting; they change no score. |
| `out/` | `pair_scores.csv`, `author_summary.csv`, `results.json` (the Claude panel). `out/gemini/`, `out/vendor_groups/` and `out/claude_plus_gemini/` hold the same files under the other panels, and `out/vendor_comparison.csv` sets them side by side. |
| `reports/Fixing the panel's overconfidence.md` | Whether giving judges participant personas, or more sampling noise, makes the model panel behave more like people on the public human data. Numbers in `reports/calibration_numbers_persona_noise.json`. |
| `reports/Prediction score change.md` | Why and how the prediction score changed on 22 November (distance to the predicted range, plus a requirement that a pair shows its gap), and what that does to the pilot. |
| `reports/Authors predicting people.md` | A human-grounded score that needs no new participants: author models predict what people answered in two public studies, scored against the real answers and against the model panels. Numbers in `reports/predict_humans_numbers.json`, rebuilt by `pipeline/predict_humans/analyse.py`. |
| `reports/Pilot rescored with persona judges.md` | The pilot rejudged by Claude models answering as described participants (run `persona` in `judgments.csv`; Fable's judges pending), compared with the original panel on the same judge models and with Gemini. Rebuilt by `pipeline/compare_persona_panel.py`. |
| `reports/Round 2b two panels.md` | Round 2b judged again by a second, independent persona panel (run `round2b-p2`): panel-to-panel agreement, a noise-ratio test that corrects the round-2b report, judge-level resampling, and the pooled two-panel author scores. Scores in `out/round2b_p2/` and `out/round2b_pooled/`; numbers in `reports/round2b_panels_numbers.json`, rebuilt by `pipeline/round2/analyse_panels.py`. |
| `reports/Round 2b three pairs per factor.md` | Round 2b: Haiku, Sonnet and Opus each wrote two more pairs per new factor; all 27 judged together by a second persona panel. Author order on three pairs per factor, a permutation test, rerun fragility, and a test-retest that corrects round 2. Pairs in `round2/vignettes_b.json`; run `round2b`; scores in `out/round2b/`; numbers in `reports/round2b_numbers.json`, rebuilt by `pipeline/round2/analyse_b.py`. |
| `reports/Round 2 contested factors.md` | Round 2: three contested factors (inevitable harm, knowledge and causation, luck and wrongness) replace the pilot's three easy ones. New pairs from Haiku, Sonnet and Opus, new classic controls anchored to public human data, a persona panel, a test-retest on the reused pairs and a rerun-fragility check. Pairs in `round2/vignettes.json`; run `round2` in `judgments.csv` and `audits.csv`; scores in `out/round2/`; numbers in `reports/round2_numbers.json`, rebuilt by `pipeline/round2/analyse.py`. `pipeline/round2/` holds the builder (brief, controls, batches, provenance check, ingestion) and the raw answers. |
| `reports/Pilot rescored with Gemini.md` | The pilot rescored with two Gemini models as a second judge group: where the vendors agree, where they differ, and how the author ranking moves. Rebuilt by `pipeline/compare_vendor_panels.py`. |
| `pipeline/` | Author brief, controls, batch randomisation, panel scripts, ingestion, and raw outputs. The human response importer requires the separate survey manifest. `pipeline/calibration/` holds the calibration run: batch and recognition builders, the panel's answers, judge provenance and the analysis. `pipeline/predict_humans/` builds and scores the "predict the people" task (predictions, provenance, analysis). `pipeline/api_panel.py` runs another vendor's models as judges through an API (manifest `batches_gemini.json`, answers in `raw/panel_gemini/`). |

## Rerun

```bash
python3 score.py
```

Python 3.9 or later, standard library only. Options: `--run` (which `run_id` to
score; several separated by commas), `--audit-run` (which run's audits to use, by
default the same), `--out`, `--no-report`, `--boot` (bootstrap resamples), `--seed`,
`--prediction-rule` (`distance`, the current rule, or `classes`, the pilot's original
rule; see `reports/Prediction score change.md`).
`judgments.csv` holds the Claude panel as run `main`, the Gemini panel as run
`gemini`, the persona panel as run `persona` and round 2 as run `round2` (score it with `--vignettes round2/vignettes.json --run round2 --audit-run main,round2`) and round 2b as runs `round2b` and `round2b-p2`, two panels on the same pairs (`--vignettes round2/vignettes_b.json --run round2b --audit-run main,round2,round2b`; `--run round2b-p2` for the second panel, `--run round2b,round2b-p2` for both pooled); the default scores `main` only. To refresh the page's side-by-side section
after either panel changes, run `python3 pipeline/compare_vendor_panels.py`, which
rescores both panels and rebuilds `results.html`.

## Adding judges or authors

- **More judges (another vendor's model, or people):** append rows to `judgments.csv`.
  Set `judge_type` (`llm` or `human`), `judge_vendor`, `judge_model`, a `judge_group`
  (the stratum that gets equal weight, for example `openai/<model>` or
  `human/prolific-us`) and a unique `judge_id` per rater. A judge must never see both
  versions of a pair; `score.py` checks this. `pipeline/api_panel.py` does all of this for
  any model behind an OpenAI-compatible endpoint, with the Claude judges' prompt and a
  spending cap.
- **More authors:** add pairs to `vignettes.json` with a new `author` block and
  collect judgments for them.
- **More auditors:** append rows to `audits.csv`.

## Licence

MIT. See `LICENSE`. It covers the code, the data files and the documentation in this repository.
