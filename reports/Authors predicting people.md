# Authors predicting people: a human-grounded score from public data

*22 November 2026. Numbers come from `reports/predict_humans_numbers.json`, which `pipeline/predict_humans/analyse.py` rebuilds. Three of the four pilot authors are scored; Fable could not run because the account hit its Fable usage limit, which resets on 26 November 2026 at 10:00 UTC.*

## Bottom line

The pilot scores authors against a panel of models. This task scores them against people. Each author model read stories from two public studies and predicted what the participants answered:

- **OffTheRails:** 10 moral scenarios × 8 versions, about 23 people per version, each rating two statements from 1 to 5.
- **MoCa:** 85 near-identical pairs of causal and moral stories, 25 people per story answering yes or no.

1. **Opus predicts people best of the three, on both datasets.** It is first on the pilot's prediction score, on average error, on its predicted average ratings, and on MoCa. The pilot, scored against the Claude panel, ranked Opus third of four. One caution: Opus named both datasets in the earlier recognition check, so part of its lead may be memory.
2. **Asking a model what people will do works at least as well as simulating people with a model panel, and on MoCa better.**

   | Predictor | Correlation with people's gaps, MoCa | Average error, MoCa |
   |---|---|---|
   | Opus's prediction | 0.56 | 0.23 |
   | Haiku's prediction | 0.45 | — |
   | Sonnet's prediction | 0.40 | — |
   | Claude panel, measured | 0.23 | 0.32 |
   | Gemini panels, measured | — | 0.28–0.35 |
   | Always "no difference" | — | 0.26 |

   The panels' measured gaps are further from people than always guessing no difference.
3. **On OffTheRails, always predicting "no difference" beats every model** on the pilot's prediction score (0.875, against Opus's 0.79) and on average error. People's gaps there are mostly smaller than the pilot's "small effect" threshold, so the score rewards caution. If human data replaces the panel, the prediction score needs changing; see the recommendations.
4. **Everyone gets acting vs not preventing backwards relative to these people.** All three authors and the Claude panel expect not preventing a colleague's harmful act to be more permissible than doing it yourself; these participants leaned slightly the other way. Correlation with people on that contrast: −0.33 to −0.36 for every author and the panel. This is the nearest analogue to the benchmark's doing-vs-allowing factor, though it also changes who acts.

## What was run

| | OffTheRails (Exp. 2) | MoCa |
|---|---|---|
| Items | 10 scenarios × 8 versions | 89 stories in 25 groups of look-alikes, forming 85 pairs |
| What people did | ~23 people per version rated two statements, 1–5 | 25 people per story answered yes or no |
| What authors predicted | The mean rating of each statement for each version | The share of people answering yes for each story |
| Scored on | 60 factor contrasts (10 scenarios × 3 factors × 2 statements), the same contrasts as the panel calibration | The 85 pair gaps |
| Best possible correlation, given people's own noise | 0.82 | 0.93 |

- **Authors:** Haiku, Sonnet and Opus, each run twice with the order of scenarios, versions, groups and stories reshuffled. Their two runs are averaged.
  - Predictions were stable: run-to-run correlation 0.97 on OffTheRails and 0.82–0.96 on MoCa.
- **What authors were told:** what the versions differ in; that the means and side-effect versions are different stories (see the correction in the calibration report); how many people answered; and to predict what people actually answered, not the right answer. They were not told the datasets' names.
- **Provenance:** every run was served the model requested. Each read only its own task file and wrote only its predictions; `pipeline/predict_humans/check_agents.py` checks this from the transcripts.

## OffTheRails: 60 contrasts

| Predictor | r with people | Average error | Mean \|predicted gap\| | Pilot prediction score | Direction right (of 60) | Same sign where people show a gap (of 20) |
|---|---|---|---|---|---|---|
| Opus | 0.47 | 0.26 | 0.25 | 0.79 | 43 | 19 |
| Sonnet | 0.46 | 0.32 | 0.37 | 0.71 | 37 | 19 |
| Haiku | 0.52 | 0.37 | 0.46 | 0.61 | 32 | 19 |
| Always "no difference" | — | **0.20** | 0 | **0.875** | 50 | 0 |
| Claude panel (measured) | 0.51 | 0.36 | 0.39 | 0.68 | 35 | 18 |
| Gemini 4 Argon (measured) | 0.60 | 0.42 | 0.50 | 0.59 | 31 | 19 |
| Gemini 3 Flash (measured) | **0.72** | 0.31 | 0.42 | 0.68 | 35 | 19 |

*People's mean |gap| is 0.20 on the 1–5 scale. The pilot's thresholds, rescaled to 1–5, call a gap under 0.33 "no difference" and one of 1.0 or more "large". "Direction right" includes correctly predicting no difference.*

**By factor:**

| Factor | What happened |
|---|---|
| Avoidable vs unavoidable harm (near-minimal edit) | Every author orders the scenarios almost exactly as people do (r 0.94), better than any panel (0.73–0.83). Opus predicts the right pattern but at a third of the size (mean \|gap\| 0.10 against people's 0.29). Haiku's sizes are closest (error 0.11). |
| Means vs side effect (two different stories) | Authors, like the panels, predict much bigger gaps than people show: Haiku 0.93, Sonnet 0.73, Opus 0.48, against people's 0.20. Opus exaggerates least. |
| Acts vs does not prevent | People's gaps are tiny (0.11), so everyone scores well on the pilot's rule. But the ordering is backwards for every author and the Claude panel (r −0.33 to −0.36). |

**Average ratings, not just gaps.** People's mean ratings across the 80 versions were 4.08 for permissibility and 2.20 for intention.
- **Opus** is closest: it predicted 4.00 and 2.25, with average errors of 0.22 and 0.28 per version.
- **Haiku** predicted permissibility far too low: 3.43, error 0.67.

## MoCa: 85 pairs

| Predictor | r with people | Average error | Where people differ by 0.30 or more (34 pairs): same / no gap / opposite | Norm-violation pairs: r, same sign of 19 |
|---|---|---|---|---|
| Opus | **0.56** | **0.23** | **28 / 1 / 5** | **0.85, 19** |
| Haiku | 0.45 | 0.26 | 22 / 1 / 11 | 0.69, 16 |
| Sonnet | 0.40 | 0.25 | 21 / 6 / 7 | 0.70, 16 |
| Always "no difference" | — | 0.26 | 0 / 34 / 0 | — |
| Claude panel (measured) | 0.23 | 0.32 | 15 / 12 / 7 | 0.41, 10 |
| Gemini 4 Argon (measured) | 0.44 | 0.35 | 17 / 17 / 0 | 0.65, 10 |
| Gemini 3 Flash (measured) | 0.38 | 0.28 | 13 / 19 / 2 | 0.64, 8 |

- **Norm violations** are the analogue of the benchmark's fifth factor (rule-breaking makes someone more of a cause).
  - The authors' predictions track people far better than any panel.
  - Opus gets the direction right on all 19 pairs where people differ clearly.
- **Agent awareness** (6 clear pairs): Opus 4 right, Haiku 3, Sonnet 2. The Claude panel got 1.
- **Predicting each story's yes-share** (not the gap): correlation 0.38–0.48, majority answer right 63–64% of the time, for all three.

## Caveats

- **This is prediction, not authoring.** It scores the "predict how readers react" half of the benchmark, on other people's stories. It says nothing about whether an author can write a pair that works.
- **Memory may help.** In the recognition check, Opus named OffTheRails for all 10 scenarios and named MoCa or BIG-Bench for 45 of 89 stories. Haiku recognised 8 MoCa stories and misattributed OffTheRails. Haiku still reaches r 0.45 on MoCa, so recognition isn't everything, but Opus's lead could partly be recall.
- **These are two particular studies.** One online sample each, and mostly small effects. A factor where people react strongly would test predictions more sharply.
- **Means vs side effect is not a clean factor in OffTheRails.** The two versions are different stories.

## What this means for the benchmark

1. **Use this as the benchmark's human-grounded component now.** It needs no new participants, costs nothing per run beyond the model calls, and gives a ranking against people rather than against models. Rerun it whenever an author model is added. Add Fable once its limit resets.
2. **Fix the prediction score before it meets human data.** *(Done 22 November: see `reports/Prediction score change.md`.)*
   - With mostly small human effects, "always no difference" wins on the pilot's thresholds. Score the error against the human gap instead of size classes.
   - For authored pairs, keep the separate "demonstrated" requirement: the pair must actually show a gap in people. Then predicting "none" can't win.
3. **Be wary of textbook expectations on doing vs allowing.** Authors and panels share the expectation that doing is worse than allowing. These participants didn't follow it. The benchmark's doing/allowing pairs are where authors' predictions and the panel's verdicts are most likely to agree with each other and both be wrong.
4. **For a prior on the pilot's pairs, a strong author's direct prediction may beat the panel's measurement.** On MoCa it did (r 0.56 against 0.23). That suggests asking Opus to predict the human gap for each pilot pair, and using that alongside the panel when the survey data are analysed.

## Rerun

```bash
python3 pipeline/predict_humans/build.py --moral-evals ext/moral-evals --moca ext/moca --out pr
```

Then, for each author model and each of `otr_r1`, `otr_r2`, `moca_r1` and `moca_r2`, give a fresh agent this instruction: read `pr/<file>.txt`, follow its instructions, and write `<model>_<file>.json`. The predictions used here are in `pipeline/predict_humans/predictions/`.

```bash
python3 pipeline/predict_humans/check_agents.py --transcripts <subagent transcript dir> --out pipeline/predict_humans/provenance.json
```

```bash
python3 pipeline/predict_humans/analyse.py --predictions pipeline/predict_humans/predictions --moral-evals ext/moral-evals --out reports/predict_humans_numbers.json
```
