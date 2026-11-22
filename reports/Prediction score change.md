# The prediction score: from size classes to distance, with a demonstration requirement

*22 November 2026. The rule is in `score.py` (`RULES["prediction_rule"]`, `prediction_score_distance`). `python3 score.py --prediction-rule classes` reproduces the original results exactly.*

## What changed

| | Original rule ("classes") | New rule ("distance") |
|---|---|---|
| What it compares | Predicted direction and size class with the observed class | The measured gap with the range the prediction names |
| Credit | Half for direction, half for size class (a neighbouring class earns half of that half); opposite direction earns 0 | 1 inside the range, falling linearly to 0 at 1.5 points outside it |
| A pair that should show a gap but doesn't | Can still score, e.g. a "small" prediction with no confirmed gap earns 0.25 | Earns 0. Applies to authored pairs and classic controls |
| Predicting "no difference" | Earns full credit wherever the gap is small | Earns 0 on an authored pair, which is meant to show a gap |

The ranges are the pilot's own bins on the 1–7 scale: no difference is under 0.5 points either way, small is 0.5 to 1.5, large is 1.5 or more. Null controls keep only the distance part, since they are meant to show nothing.

## Why

- **The original rule rewarded caution.** Tested against real people on public data (`reports/Authors predicting people.md`), always predicting "no difference" beat every model on it: 0.875 against Opus's 0.79. People's effects there were mostly below the "small" line. An author scored that way could do well by never committing to an effect.
- **It also mis-scored near misses and large misses.**
  - Fable's moral-luck pair measured −1.50, a hair inside "small", and lost a quarter of its score.
  - Haiku's knowledge pair, predicted small, measured a 4-point gap and still kept 0.75.

## What it does to the pilot

**An author who predicted "no difference" for every pair** would have scored 0.19 (Claude panel), 0.16 (Gemini) or 0.26 (persona panel) under the original rule. On these panels the pilot's gaps are mostly large, so the loophole wasn't being used here. It would matter on human data. Under the new rule that author scores 0.

**Authors, Claude panel:**

| Author | Mean prediction score, original → new | Mean composite, original → new |
|---|---|---|
| sonnet | 1.00 → 1.00 | 81.3 → 81.3 |
| fable | 0.80 → 0.80 | 76.7 → 76.7 |
| opus | 0.85 → 0.80 | 74.6 → 72.6 |
| haiku | 0.65 → 0.47 | 63.7 → 56.6 |

The order is unchanged under every panel:
- Sonnet first under the Claude panel and the six-model average.
- Fable first under Gemini, the two-vendor scoring and the persona panel.
- Haiku last everywhere.

**Pairs whose prediction score changes** (Claude panel):

| Pair | Predicted | Measured gap | Original → new | Why |
|---|---|---|---|---|
| Haiku, knowledge (Scanner beep crate) | A higher, small | +4.05 | 0.75 → 0 | 2.55 points beyond the "small" range |
| Haiku, moral luck (Rogue wave hatch) | B higher, large | −0.95 | 0.75 → 0.63 | 0.55 points short of "large" |
| Haiku, norm violation (Gate and rogue van) | A higher, small | +1.90 | 0.75 → 0.73 | 0.40 points beyond "small" |
| Opus, doing vs allowing (Greenhouse window) | A higher, small | +0.20, not confirmed | 0.25 → 0 | No confirmed gap |
| Fable, norm violation (Storage shelf) | A higher, small | +0.35, not confirmed | 0.25 → 0 | No confirmed gap |
| Fable, moral luck (Garden fire) | B higher, large | −1.50 | 0.75 → 1.00 | On the boundary of "large" |

Because the best and worst pairs change, two new cards on the page carry hand-written notes: Fable's moral-luck pair among the best three, Haiku's knowledge pair among the worst three.

**Sensitivity:** with the fall-off at 1.0 or 2.0 points instead of 1.5, only Haiku's mean moves (0.41 and 0.51 instead of 0.47). The other three are unaffected and the order holds.

## Caveats

- **The rule changed after the data were seen.** It's a post-hoc change. The original scores are kept beside the new ones: in grey on the results page, in `prediction_score_classes_rule` in `out/pair_scores.csv`, and with `--prediction-rule classes`. The methods note lists it as judgment call 11.
- **The 1.5-point fall-off is a choice.** It equals the "large" threshold: one size band beyond the predicted range costs about two-thirds of the credit. The sensitivity check above shows it barely matters here.
- **On human data, the demonstration requirement depends on sample size.** A real but small effect measured with too few people may not be confirmed, and then scores 0. The survey's sample size has to be set with that in mind (see `docs/human-survey.md` and the mathematical analysis), or the threshold for "confirmed" adapted to the human run.
- **The class results are still reported.** "Direction right", "size right" and "both right" are unchanged; only the score that feeds the composite changes.
