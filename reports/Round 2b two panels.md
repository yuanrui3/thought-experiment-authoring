# Round 2b, judged by two independent panels

*22 November 2026. A second persona panel (run `round2b-p2`) judged exactly the round-2b batches' items: the same 37 pairs, with new personas and new random orders and version assignments. Scores: `out/round2b/` (panel 1), `out/round2b_p2/` (panel 2), `out/round2b_pooled/` (both panels' ratings together; under the unchanged rules that is one panel with 10 ratings per model and version instead of 5). Every number below is rebuilt by `python3 pipeline/round2/analyse_panels.py` into `reports/round2b_panels_numbers.json`.*

## Bottom line

- **The two panels agree on the gaps, to within sampling noise.**
  - Gaps correlate 0.94 across all 37 pairs (0.96 across the 27 authored pairs), with a mean difference of 0.28 points.
  - The squared differences are exactly what each panel's own error predicts: a ratio of 1.07 (1.00 would be pure noise). Model by model it is 0.98.
- **This corrects the round-2b report. There is no extra per-run shift.**
  - Round 2 against round 2b also comes out at sampling noise: 1.00 and 0.80 on gaps, and 1.10 and 1.30 model by model. That is at most a weak hint that a different batch mix matters.
  - What looked like a run shift is the scoring rule. A gap must clear 0.5 points, its interval must exclude zero, and all three judge models must agree. With 5 ratings per model and version, ordinary noise carries many gaps across one of those lines.
- **Resampling whole judges predicts this correctly.** It forecast 5.7 changed scores among the 27 authored pairs between panel 1 and a rerun; panel 2 changed 5. The rating-level resampling used before understated it.
- **Two panels pooled halve the instability.**
  - Expected score changes in a rerun fall from 5.7 to 2.6.
  - The rerun spread of an author's mean falls from about 0.16 to about 0.09.
- **Pooled, the authors are:**

  | Author | Prediction score | Composite |
  |---|---|---|
  | Sonnet | 0.98 | 80.6 |
  | Opus | 0.98 | 83.2 |
  | Haiku | 0.78 | 70.4 |

  - Haiku is last in 83% of judge resamples.
  - But a permutation test across pairs gives p = 0.13 against Sonnet and p = 0.16 against Opus. Haiku's lower score is a reliable measurement of these nine pairs, but it is not yet shown to be a trait of the author.
- **The benchmark has hit a ceiling again, and two classic controls fail.**
  - Pooled, 26 of the 27 authored pairs show their predicted gap, and the mean prediction score is 0.91. On these factors, with "small" as the usual prediction, Sonnet and Opus can't be separated.
  - Two classic controls fail in both panels for one reason: the Haiku judges sit at the top of the scale on blame and wrongness questions, so their gap is near zero and blocks the agreement rule.

## The two panels, pair by pair

| | Panel 1 | Panel 2 | Pooled |
|---|---|---|---|
| Authored pairs that show their predicted gap | 24 of 27 | 23 of 27 | 26 of 27 |
| ... with all three judge models agreeing | 26 of 27 | 23 of 27 | 26 of 27 |
| Mean prediction score, authored pairs | 0.84 | 0.80 | 0.91 |
| Mean size of gap, authored pairs | 1.27 | 1.35 | 1.31 |
| Classic controls reproduced | 3 of 5 | 2 of 5 | 2 of 5 |
| Null controls crossing the line | 0 of 5 | 1 of 5 (0.60) | 0 of 5 (largest 0.27) |

Five authored pairs change score between the panels:
- Haiku's rail and rockfall pairs (avoidable harm) and its kayak pair (luck);
- Sonnet's babysitter pair;
- Opus's café Wi-Fi pair (luck).

In four of the five, one judge model's sign flipped, so the agreement rule turned the verdict on or off. In the fifth, Sonnet's babysitter, the gap crossed the 0.5 line (−0.40 in panel 1, −1.07 in panel 2). Of the nine round-2 pairs, the two panels give the same score to eight. Round 2 gave a different score to four or five of them.

## Authors

| Author | Panel 1 | Panel 2 | Pooled | Pooled, by factor (avoidable harm / knowledge / luck) |
|---|---|---|---|---|
| Opus | 0.98 (83.4) | 0.84 (77.6) | 0.98 (83.2) | 1.00 / 0.93 / 1.00 |
| Sonnet | 0.88 (76.5) | 0.97 (80.3) | 0.98 (80.6) | 1.00 / 0.95 / 1.00 |
| Haiku | 0.66 (65.5) | 0.59 (62.9) | 0.78 (70.4) | 0.87 / 1.00 / 0.48 |

*Mean prediction score, with mean composite in brackets.*

- **Opus and Sonnet swap places between panels,** and pooled they tie on prediction. Opus stays ahead on the composite because auditors rated its pairs cleaner (confound severity 0.67 against 0.89) and a little more original (1.44 against 1.33).
- **Haiku is last in both panels and pooled.** Its deficit sits in the luck factor: it predicted large gaps that came out small, and its roofer pair shows no gap. Pooled, its knowledge pairs are perfect.
- **Judge-level resampling of the pooled panels:**

  | Order | Share of resamples |
  |---|---|
  | Sonnet > Opus > Haiku | 63% |
  | Opus > Sonnet > Haiku | 20% |
  | Sonnet > Haiku > Opus | 10% |
  | Other orders | 7% |

## Controls

| Control | Panel 1 | Panel 2 | Pooled | Why it fails |
|---|---|---|---|---|
| The bike lanes (avoidable harm and intention) | −0.27 | 0.00 | −0.13, none | The panel rates intention near the floor in both versions. A known blind spot (people: +0.71 on 1–5) |
| The pencil box (knowledge) | +1.07 | +1.60 | +1.33, reproduced | |
| The bath (luck and wrongness) | +0.93 | +0.47 | +0.70, unclear | The Haiku judges sit near 7 in both versions; in panel 2 their gap is −0.6 |
| Doing vs allowing | +1.07 | +0.93 | +1.00, unclear | The Haiku judges rate both versions about 6.5, with a gap of −0.2 in both panels |
| Norm violation | +1.73 | +1.80 | +1.77, reproduced | |

**The agreement rule makes each verdict depend on the least sensitive judge model.** Here that is Haiku at the ceiling of the scale. Both failures are stable across panels, so they are not noise.

## What this means

1. **Use at least 10 ratings per model and version** (two panels' worth). The gaps were already reproducible. What wasn't reproducible was the verdict at the threshold, and doubling the ratings halves the expected flips.
2. **Report judge-level resampling as the error bar.** It predicted the second panel's changes (5.7 against 5). Resampling single ratings understated them.
3. **Comparing runs is less dangerous than the round-2b report said.** Gaps from different runs agree within noise. Scores near a threshold do not, so a comparison across runs needs the same rating count and an error bar.
4. **The agreement rule needs a decision from you.** With three judge models, one model at the ceiling vetoes real gaps, including two classic controls. Options:
   - require two of three models;
   - drop Haiku as a judge on blame and wrongness questions;
   - judge agreement by an interval that resamples models.

   Any of these is a post-hoc rule change, so I have not made one.
5. **The ceiling is now the limit on discrimination.** Sonnet and Opus get 0.98. To tell them apart the task needs a sharper target: the predicted gap in points scored by distance with no tolerance band, a required size, or factors whose gaps are less predictable.

## Corrections to earlier reports

- **`reports/Round 2b three pairs per factor.md`** said a panel run carries its own shift, larger than the noise within it. The two panels show it doesn't: gap differences match sampling noise. The large score changes between runs come from thresholds acting on noisy gaps, measured against a fragility check that was too optimistic. Its author ranking (Opus 0.98, Sonnet 0.88, Haiku 0.66) was one panel; pooled, Sonnet and Opus tie.
- **`reports/Round 2 contested factors.md`:** the withdrawal of "the new factors are harder" stands. The same pairs scored 0.44 in round 2 and 0.84 in round 2b's first panel (0.91 pooled), so a one-panel factor comparison can't support it. The reason is now noise and thresholds, not a run shift.

## Judgment calls

1. **Panel 1 is round 2b's existing run.** Panel 2 is new, with the same items and design and a new seed. I did not run a third panel; two give the comparison, and pooling them gives 10 ratings per cell.
2. **Batch composition was held fixed,** so that the difference between panels measures judge noise alone. The question of context is answered only by round 2 against round 2b, where the evidence for it is weak.
3. **No scoring change.** The pooled panel is scored by the same rules, treating it as a larger panel.
4. **Three Haiku judges made a call after writing their answers.** Two tried to report back, and one sent "done" to this session. Their answers were already written, so all 30 count.
