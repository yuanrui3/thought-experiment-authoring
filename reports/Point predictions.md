# A sharper target: predicting the gap in points

*24 November 2026. Design, scoring and pass mark were committed before any prediction was collected (commit be5114e, `pipeline/round2/point_predictions.py`). Predictions are in `pipeline/round2/raw/point_predictions/`, and numbers in `reports/point_predictions_numbers.json`, rebuilt by `python3 pipeline/round2/point_predictions.py analyse`. No new judging and no API credit: three agents, scored against gaps already measured.*

## Bottom line

- **On the benchmark's own measure, a number doesn't separate Sonnet from Opus.** Each author predicted the gap for its own 9 pairs:

  | Author | Mean error |
  |---|---|
  | Opus | 0.39 points |
  | Sonnet | 0.52 points |
  | Haiku | 0.60 points |

  - Opus is ahead of Sonnet in 87% of judge resamples, against a pass mark of 90%.
  - A permutation test gives p = 0.49 against a pass mark of 0.05.
  - So it fails the mark set in advance. With 9 pairs each, pair-to-pair variation swamps the difference: Opus's own errors run from 0.0 to 1.0.
- **Predicting all 37 shared items, Opus is clearly better:**

  | Predictor | Mean error | Correlation with the measured gaps |
  |---|---|---|
  | Opus | 0.34 | 0.93 |
  | Haiku | 0.58 | 0.89 |
  | Sonnet | 0.61 | 0.81 |

  - Opus beats Sonnet (p = 0.009) and Haiku (p = 0.003) in a paired test.
  - Opus comes out best in every judge resample.
  - Measurement is not the limit: a perfect predictor would still miss by about 0.14 because the measured gaps are noisy.
- **A number adds little over the old size classes for an author's own pairs.**
  - Each author's original prediction at writing time, turned into a number (small = 1.0, large = 2.0), did as well or better: Opus 0.39 (same), Haiku 0.58 (same), Sonnet 0.30 (better than its 0.52).
  - Sonnet predicted "small" for all nine pairs, and its gaps mostly landed near 1.0.

## What was done

- **Items:** the 37 round-2b items, meaning the 27 authored pairs (9 each by Haiku, Sonnet and Opus) and the 10 controls. Each was under a neutral code, and authors were not named.
- **Predictors:** Haiku, Sonnet and Opus, each in a fresh context, each predicting all 37 items. None was told which pairs were its own, and none saw any result or any earlier prediction.
- **What they were told:** how the readers judged (persona model judges, one version per reader, mixed with 36 other scenarios, 10 ratings per model and version), and what to predict (mean rating A minus mean rating B, averaged over the three judge models, one decimal).
- **Target:** the gaps measured by the two round-2b panels pooled, recomputed at full precision from the ratings.
- **Provenance:** all three read only their task file before writing. Haiku made two documentation lookups after writing its answers and said so; under the committed rule that doesn't affect usability.

## Results by author, own pairs

| Author | Mean error | Point score | Class-midpoint baseline | Noise floor | Avoidable harm | Knowing the rule | Luck and wrongness |
|---|---|---|---|---|---|---|---|
| Opus | 0.39 | 0.74 | 0.39 | 0.14 | 0.41 | 0.70 | 0.07 |
| Sonnet | 0.52 | 0.65 | 0.30 | 0.14 | 0.28 | 0.41 | 0.88 |
| Haiku | 0.60 | 0.60 | 0.58 | 0.13 | 0.31 | 0.44 | 1.04 |

*Mean absolute error, in points on the 1–7 scale. Point score = max(0, 1 − error / 1.5), averaged.*

- **Judge resamples by order:** Opus, Sonnet, Haiku in 74%; Opus, Haiku, Sonnet in 13%; Sonnet, Opus, Haiku in 12%.
- **Haiku against Opus:** 99% of resamples agree, but the permutation test across pairs doesn't (p = 0.32). The pass mark asked for both.

## Where the predictions go wrong

The three models share two systematic errors:

- **They expect bad outcomes to make a choice look more wrong than the panel shows.**
  - On their luck pairs, Haiku and Sonnet predicted gaps of 1.5 to 2.7 points. The panel gave 0.4 to 1.4.
  - Opus predicted its own luck pairs almost exactly. It also wrote them so the harmful version came first, though that shouldn't matter.
- **They expect knowing the rule to matter less for causation than it does.** All three predicted 0.8 to 1.0 points on knowledge pairs. The panel gave 1.1 to 1.7.

The largest single miss is Opus's airport pair: it predicted 2.8, and the panel gave 1.8.

## What this means

1. **Predicting the gap in points for one's own pairs is not enough on its own.** At 9 pairs per author it fails the pass mark. The errors depend more on the pair than on the author, and a number didn't beat the size classes the authors already gave.
2. **What does separate the authors is predicting a shared pool.** With every predictor scored on the same 37 items, Opus stands clear of Sonnet and Haiku. That is a different measure: predicting readers in general, not designing pairs whose effect you can predict. A benchmark could keep both:
   - the authoring score (does the pair show its gap, how clean is it, how original);
   - a prediction score on a common pool that includes other authors' pairs.
3. **The full "target size" round (option 2) is not worth running yet** for this purpose. It would still score authors on their own few pairs, where this test found no separation.

## Caveats

- **The target is a model panel, not people.** Its judges are Haiku, Sonnet and Opus with personas, so a model may be predicting partly itself. Sonnet is on the panel too, though, and did worst on the shared pool.
- **The class-midpoint baseline is not a like-for-like comparison.** It came from the authoring instance, at writing time, with the full brief. The numbers came later, from a fresh instance with a shorter description.
- **This is one prediction per model per item.** A rerun of the same agents would vary too; that spread was not measured.
- **The task text gave away a little.** It said gaps "in this study ran from about -2 to about +3", a range taken from the results being predicted. All three predictors saw the same sentence, so the comparison between them is fair, but it is outcome information they shouldn't have had. The shared-pool task text (`pipeline/shared_pool.py`) states only what earlier rounds showed.
- **Fable is missing** (usage limit until 26 November). It can predict the same 37 items with the same task file. It wrote none of them, so it would count on the shared pool only.
