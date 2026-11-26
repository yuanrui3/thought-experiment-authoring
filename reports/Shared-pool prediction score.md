# The shared-pool prediction score

*Adopted 25 November 2026 at the owner's request ("option B"), and committed before any prediction for the next round was collected. The definition is in `pipeline/shared_pool.py`. The worked example below is in `reports/shared_pool_round2b_numbers.json`.*

## What it is

A second score, reported beside the composite and never folded into it.

*Update, 26 November: at the owner's request, after round 2c, a summary score now averages the composite and this score with equal weight. Both are still reported unchanged beside it. See `reports/Summary score.md`.*

- **Pool:** every item of a round, meaning all authored pairs and all controls, under neutral codes.
- **Who predicts:** every author of the round, each in a fresh context, each predicting every item as a gap in points (mean rating of A minus mean rating of B).
- **When:** after all pairs are written and before any judging of the round starts.
- **Against what:** the round's measured gaps, from all its panels pooled.
- **Headline:** the shared-pool score, 0–100. It is 100 × the average over the items the predictor did not write of max(0, 1 − |predicted − measured| / 1.5).
  - That is the distance rule applied to a point prediction, on other authors' pairs and the controls.
  - Beside it, in points: the average miss on those items, on all items, and on the predictor's own pairs.
- **Comparing two authors:** only on the items neither of them wrote, with a paired sign-flip test.
- **Error bar:** judge-level resampling, which predicted the real panel-to-panel changes in round 2b.

## Why

- **On their own nine pairs, Sonnet and Opus could not be told apart.** Mean errors were 0.52 and 0.39 points, and the difference failed the pass mark set in advance (`reports/Point predictions.md`).
- **Own-pair prediction can reward playing safe.** An author who always predicts "small" and writes pairs that land near 1 point does well without showing much.
- **A shared pool scores every author on the same items.** That is far more statistical power for the same cost: one agent per author per round, with no extra judging.

## What it is not

It measures how well an author predicts what readers do with pairs it didn't write. That is part of authoring skill, not all of it. The composite still scores whether an author's own pairs show their predicted gap, how clean and original they are, and whether readers understand them.

## Worked example: round 2b (post hoc, not a real use)

The round-2b point predictions were made blind, but after the round was judged, and their task text gave away the range of the gaps. So they don't meet the definition and serve only to test the code.

| Predictor | Shared-pool score | Mean error, others' pairs and controls (28 items) | Own pairs (9) | All 37 |
|---|---|---|---|---|
| Opus | 78.3 | 0.33 | 0.39 | 0.34 |
| Sonnet | 62.3 | 0.64 | 0.52 | 0.61 |
| Haiku | 62.1 | 0.57 | 0.60 | 0.58 |

- **Opus is first in every judge resample.** Sonnet and Haiku split second place (42% and 58%).
- **On the 19 items written by neither of the two:** Opus against Sonnet p = 0.05, Opus against Haiku p = 0.04, Haiku against Sonnet p = 0.26.
  - Excluding each author's own pairs leaves fewer shared items than the 37 used in the point-prediction test, which is why these p-values are weaker.
  - Round 2c will have 46 items, of which 28 are written by neither of any two authors.
- **Sonnet predicts its own pairs better than others' (0.52 against 0.64).** Opus and Haiku don't. It is one data point, but it is why the headline excludes an author's own pairs.

## First real use

*Done on 26 November; results in `reports/Round 2c Fable joins.md` and `reports/shared_pool_round2c_numbers.json`.*

- Fable 72.2, Opus 69.9, Sonnet 62.0, Haiku 57.0.
- On the 28 items written by neither of the two: Fable and Opus tie (p = 0.77), Opus beats Sonnet again (p = 0.02), and Fable beats Haiku (p = 0.006).
- Sonnet again predicted its own pairs better than others' items (0.51 against 0.57). Fable, Opus and Haiku did not.

Round 2c ran after Fable's usage limit reset (26 November). All four authors had written their pairs. Before any judging, each predicted all 46 items:

```bash
python3 pipeline/shared_pool.py build --vignettes round2/vignettes_c.json --models haiku sonnet opus fable --tag c --out <scratchpad>/spc --manifest pipeline/round2/shared_pool_manifest_c.json
```

The agents read `<scratchpad>/spc/<model>.txt` and write `<scratchpad>/spca/<model>.json`. After judging, run `check` and `score` with the round's runs.
