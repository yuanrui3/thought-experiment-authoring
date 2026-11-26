# Summary score: composite and shared-pool score with equal weight

*Adopted 26 November 2026 at the owner's request ("go ahead with equal weight for the shared-pool score"). The definition is in `pipeline/summary_score.py`; round-2c numbers are in `reports/summary_round2c_numbers.json`, rebuilt by that script.*

**This was decided after the round-2c results were known.** The weights are now fixed and apply unchanged to every later round. Under them, Fable moves from third to second in round 2c, and Opus stays first.

## What changes

- **One summary number per author and round:**

  summary = 0.5 × composite + 0.5 × shared-pool score

  Both parts are on a 0–100 scale. The composite and the shared-pool score are still reported beside it, and neither is changed.
- **It applies only to rounds with a shared-pool score:** round 2c onwards. The pilot's results page has no shared-pool score and keeps the composite alone.
- **What the summary weighs, component by component:**

  | Component | Weight |
  |---|---|
  | Shared-pool prediction | 50% |
  | Own-pair prediction | 20% |
  | Confounds | 12.5% |
  | Originality | 10% |
  | Comprehension | 7.5% |

  So 70% of the summary is about predicting readers. Pair quality, as the auditors judge it, is 22.5%.
- **The weights are nominal; neither part is rescaled to the field.** Rescaling would make an author's summary depend on which other authors are in the round.
  - The cost is that the part with the wider spread between authors moves the order more.
  - In round 2c the shared-pool score spreads wider: a standard deviation of 6.1 points between authors, against 4.3 for the composite.

## Round 2c

| Author | Summary | 95% interval | Composite | Shared-pool score |
|---|---|---|---|---|
| Opus | **75.3** | 70.0 – 78.5 | **80.7** | 69.9 |
| Fable | 71.4 | 66.2 – 76.0 | 70.7 | **72.2** |
| Sonnet | 69.0 | 61.0 – 72.3 | 76.1 | 62.0 |
| Haiku | 63.5 | 57.8 – 68.9 | 70.0 | 57.0 |

*Intervals combine judge-level resampling (300 resamples) with item-level resampling (pairs within each author × factor cell, controls within their type), in 5,000 draws.*

**Opus is first in 96.5% of draws and Fable in 3.5%.**

| Comparison | Difference | 95% interval | Same sign | Clear? |
|---|---|---|---|---|
| Opus − Fable | +3.8 | −0.3 to +7.4 | 96.5% | no, just |
| Opus − Sonnet | +6.2 | +3.2 to +12.0 | 100% | yes |
| Opus − Haiku | +11.8 | +5.5 to +16.7 | 100% | yes |
| Fable − Sonnet | +2.4 | −1.1 to +10.0 | 93% | no |
| Fable − Haiku | +7.9 | +0.7 to +14.9 | 98% | yes |
| Sonnet − Haiku | +5.5 | −2.2 to +10.0 | 90% | no |

*A difference counts as clear only if its 95% interval excludes 0; the rule was fixed in the script before it was first run.*

- **Opus leads, but not clearly ahead of Fable.**
- **Opus is clearly ahead of Sonnet and Haiku, and Fable is clearly ahead of Haiku.**
- **Fable against Sonnet, and Sonnet against Haiku, are not settled.**

**How sensitive the order is:**

- **To the weights.**
  - Sonnet passes Fable only if the composite gets more than 65% of the weight.
  - Fable passes Opus only if the composite gets less than 19%.
  - So any weighting between 35/65 and 65/35 gives the same order: Opus, Fable, Sonnet, Haiku.
- **To rescaling.** Averaging standardised scores gives the same order, and so does averaging ranks (Opus 1.5, Fable 2.0, Sonnet 2.5, Haiku 4.0).
- **To the audit asymmetry in round 2c.** Fable's extra audit cost Sonnet 2.8 composite points (`reports/Round 2c Fable joins.md`). Without it, Sonnet's summary is 70.4, still third and 1.0 behind Fable.

**Known bias in the intervals.** A pair at full prediction score can only lose when the judges are resampled. So the draws sit slightly below the observed summary: by 1.5 points for Sonnet, 0.6 for Opus, 0.3 for Fable, and not at all for Haiku. This largely cancels in the differences, which is what the "clear" rule uses.

## Why equal weight

- **The two scores rank authors differently.** In round 2c, Opus and Sonnet lead the composite, while Fable and Opus lead the shared pool.
- **The own-pair prediction score, 40% of the composite, has a weakness the shared-pool score doesn't.**
  - When every author misjudges a factor's size the same way, the own-pair score ranks them by how strong their manipulation happened to be. All four predicted "small" for every knowledge pair.
  - The shared-pool score puts every predictor on the same items, so that doesn't happen.
- **The shared pool holds the only prediction difference that has replicated.**
  - Opus beat Sonnet on it in round 2b (p = 0.009) and again in round 2c (p = 0.02).
  - On own pairs, only one difference has reached p < 0.05 (Sonnet over Fable in round 2c), and it doesn't survive correction for six comparisons.
- **It agrees with the human-data check** (`reports/Authors predicting people.md`), where Fable and Opus predicted people best. That is the only measure here that doesn't rest on model judges.

## Caveats

- **The weights were chosen after seeing the round they are first applied to.** The order they give is stable across a wide range of weights (above), but the choice wasn't blind.
- **The judges are models, not people.** Both halves rest on the same persona panel, so a panel bias would show up in both.
- **Four authors and nine pairs each.** Two comparisons sit on the line: Fable over Haiku is clear by 0.7 points at the lower end of its interval, and Opus over Fable misses by 0.3. Either could go the other way in another round.

## Rerun

```bash
python3 pipeline/summary_score.py --results out/round2c/results.json --vignettes round2/vignettes_c.json --runs round2c --manifest pipeline/round2/shared_pool_manifest_c.json --answers pipeline/round2/raw/shared_pool_c --provenance pipeline/round2/raw/provenance_pool_c.json --shared reports/shared_pool_round2c_numbers.json --out reports/summary_round2c_numbers.json
```

It needs `score.py` and `pipeline/shared_pool.py score` run first for the round. It checks that its shared-pool scores match the published ones.
