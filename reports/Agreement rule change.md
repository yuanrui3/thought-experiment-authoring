# The agreement rule: from three-quarters to two-thirds of judge models

*24 November 2026. The rule is in `score.py` (`RULES["agreement_rule"]`, `set_agreement_rule`). `python3 score.py --agreement-rule three_quarters` reproduces every earlier score exactly; this was checked against all ten scored panels. Numbers below are in `reports/agreement_rule_numbers.json`, rebuilt by `python3 pipeline/compare_agreement_rules.py`. Calibration numbers under the new rule are in `reports/calibration_numbers_two_thirds.json`.*

## What changed

| | Old rule ("three_quarters") | New rule ("two_thirds") |
|---|---|---|
| Judge models whose own gap must point the same way | 75% of them, rounded up | Two-thirds of them, rounded up |
| With 3 judge models | all 3 | 2 of 3 |
| With 4 judge models | 3 of 4 | 3 of 4 (unchanged) |
| With 2 judge groups | 2 of 2 | 2 of 2 (unchanged) |
| With 6 judge groups | 5 of 6 | 4 of 6 |

The other two conditions for a confirmed gap stay: at least 0.5 points, and a 95% interval that excludes zero.

## Why

- **One judge model at the ceiling vetoed real gaps.** In both round-2b panels, the Haiku judges rated blame and wrongness questions near the top of the scale in both versions (about 6.5 against 6.5, or 7.0 against 6.4). Their own gap was near zero, so the old rule blocked gaps that Sonnet and Opus both showed at +1 to +2.4.
- **Two classic controls failed for this reason alone:** doing vs allowing and the bath (luck and wrongness).
- **Most of the run-to-run instability came from the same check.** With 5 ratings per model and version, a model near zero flips its sign from run to run (`reports/Round 2b two panels.md`).
- **You chose this option** from three on 24 November. The others were dropping Haiku as a judge on blame and wrongness questions, and an interval that resamples the models.

## What it does

**The pilot's published results don't change.** The pilot was judged by four models, and 3 of 4 is needed under either rule. The same holds for the Gemini panel and the two-vendor scoring (2 groups).

**Where three or six judge groups were used:**

| Panel | Pairs that change | Author scores (composite or prediction score), old → new |
|---|---|---|
| Pilot, persona panel (3 models) | Sonnet's moral-luck pair (−0.53, 2 of 3 models) is now confirmed | Sonnet 65.3 → 73.3. Fable still first (74.7), now narrowly |
| Pilot, 4 Claude + 2 Gemini models (6 groups) | Fable's norm pair (+0.70, 4 of 6) is now confirmed | Fable 76.7 → 84.7, now first (Sonnet 81.3) |
| Round 2 (3 models) | Haiku's solvent room (+0.67) and Opus's smoke alarm (+1.40) are now confirmed | prediction: Haiku 0.24 → 0.44, Opus 0.60 → 0.80, Sonnet 0.55 |
| Round 2b, panel 1 | Haiku's rockfall pair; the doing-vs-allowing control | prediction: Haiku 0.66 → 0.77; Opus 0.98, Sonnet 0.88 unchanged |
| Round 2b, panel 2 | Haiku's rail and kayak pairs, Opus's Wi-Fi pair; the doing-vs-allowing control | prediction: Haiku 0.59 → 0.76, Opus 0.84 → 0.95; Sonnet 0.97 |
| Round 2b, both panels pooled | No authored pair; the bath and doing-vs-allowing controls are now reproduced (classic controls 2 → 4 of 5) | Unchanged: Sonnet 0.98, Opus 0.98, Haiku 0.78 |

Every change goes the same way: a gap that two of three models showed, previously "not confirmed", is now confirmed. No verdict was lost.

**Scores are much more stable.** This is from judge-level resampling, which predicted the real panel-to-panel changes correctly under the old rule.

| | Old rule | New rule |
|---|---|---|
| Authored pairs whose score differs between panel 1 and panel 2 | 5 of 27 | 1 of 27 |
| Expected score changes in a rerun of panel 1 | 5.7 | 1.6 |
| Expected score changes in a rerun of the pooled panels | 2.6 | 0.7 |
| Rerun spread of an author's mean (panel 1) | about 0.16 | about 0.06 |
| Rerun spread of an author's mean (pooled) | about 0.09 | about 0.04 |
| Round 2 against round 2b: scored pairs that change | 6 of 14 | 3 of 14 |

**The author order is unchanged:** Haiku last everywhere (93% of resamples of the pooled panels), and Sonnet and Opus tied pooled (52% and 48% first). A permutation test across pairs still can't separate any two authors on the pooled scores (p = 0.13 and 0.16 for Haiku).

## The cost: more gaps that people don't show

The calibration on public human data (OffTheRails and MoCa) was rerun under the new rule for the two three-model Claude panels. The four-model panel there is unaffected.

| Panel | Rule | Gaps confirmed | ... that people show | ... where people show none | Share people back |
|---|---|---|---|---|---|
| Claude ×3, with personas (the panel rounds 2 and 2b use) | old | 22 | 12 | 10 | 55% |
| | new | 33 | 13 | 20 | 39% |
| Claude ×3, plain | old | 27 | 10 | 16 | 37% |
| | new | 34 | 13 | 20 | 38% |

*OffTheRails and MoCa together. The "people show none" column counts confirmed gaps where people showed no difference (out of 84 such contrasts).*

- **For the persona panel, the new rule doubles the false confirmations** (10 → 20) and finds one more real gap (12 → 13). Most of the increase is on MoCa (3 → 10 false confirmations among 44 human nulls).
- **The plain panel was already poor and stays poor.**
- **So the trade is reliability against validity.** Under the new rule a confirmed gap reproduces far more often between panels. On human data, though, two models agreeing without the third is as often a gap people don't show as one they do. The old rule's veto was partly real caution, not only a ceiling artefact.

## Caveats

- **This is a post-hoc change,** made after seeing these data, at your request. The old rule is one flag away (`--agreement-rule three_quarters` in `score.py`, `pipeline/calibration/analyse.py` and the round-2 analysis scripts). The published calibration numbers were left under the old rule, which is still that script's default.
- **The calibration contrasts are not the benchmark's pairs.** They are other people's vignettes, rated on 1–5 agreement scales (OffTheRails) or yes/no (MoCa). The false-confirmation rate there is a warning, not a measured rate for authored pairs.
- **The reports written before today quote old-rule numbers in their bodies.** Each has a short note pointing here. Their numbers files (`reports/round2_numbers.json`, `round2b_numbers.json`, `round2b_panels_numbers.json`) now hold the new rule's numbers. To rebuild the old ones, rescore with `--agreement-rule three_quarters` and run the analysis with the same flag.

## What I'd consider next

The ceiling problem has a narrower fix that may not cost as much validity: leave the rule alone and stop using Haiku as a judge where it sits at the top of the scale (option 2), or weight models by how well they track people. Either can be tested on the same calibration data before adopting it. I have not done this; you asked for option 1 only.

*Update, 26 November: option 2 was tested, with its criteria set in advance, and rejected (`reports/Ceiling abstention test.md`).*
- It costs nearly as much validity as the two-thirds rule (41% of confirmed gaps backed by people), because on MoCa's yes/no questions most models sit at a bound and abstain.
- It doesn't fix the flips.
- The test also showed that the vetoes on authored pairs mostly came from a model that saw no gap in the middle of the scale, not from one at the ceiling. The sentence above about "Haiku at the top of the scale" holds for the two classic controls only.

*Update, 26 November: weighting models by how well they track people was also tested and rejected (`reports/Judge weighting test.md`).*
- Out of sample, 45% of the persona panel's confirmed gaps are backed by people.
- Stability is as poor as the pilot rule's, because Haiku, the usual dissenter, tracks people as well as the others and keeps its veto.
- The two-thirds rule stays.
