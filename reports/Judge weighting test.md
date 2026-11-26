# Weighting judge models by how well they track people: tested and rejected

*26 November 2026, at the owner's request ("go ahead with weighting judge models by how well they track people"). The weights, the rule and the pass criteria were committed before the test ran (commit e91e970, `pipeline/test_judge_weights.py`). Numbers are in `reports/judge_weights_numbers.json` and `reports/calibration_numbers_weighted.json`, both rebuilt by that script. The rule stays available as `--agreement-rule weighted --judge-weights FILE` in `score.py` and `pipeline/calibration/analyse.py`. It is not the default.*

## Bottom line

**Weighting fails two of the three criteria set in advance, so the two-thirds rule stays.**

| Criterion (fixed in advance) | Needed | Pilot rule | Two-thirds (current) | Weighted |
|---|---|---|---|---|
| C1. Persona panel on human data, out of sample: share of confirmed gaps that people back | ≥ 50% | 55% | 39% | **45%** ✗ |
| C1. ... and human gaps it confirms | ≥ 12 | 12 | 13 | **14** ✓ |
| C2. Round 2b authored pairs whose score changes between the two panels | ≤ 2 of 27 | 5 | 1 | **6** ✗ |
| C3. No panel confirms more null controls than under the current rule | — | — | — | ✓ |

- **On human data it is a partial improvement, not enough.**
  - Out of sample, the weighted persona panel's confirmations are backed by people 45% of the time, against 39% for two-thirds.
  - It also confirms the most real human gaps of any rule: 14.
  - But it is still well short of the pilot rule's 55%, and of the 50% bar.
- **On stability it is as bad as the pilot rule.** In a rerun of round 2b's panel 1, judge-level resampling expects 5.7 score changes, the same as the pilot rule (two-thirds: 1.7).
- **Scored in sample it looks good, and that is misleading.** With weights fitted to the same data they are scored on, the persona panel reaches 57% (13 backed, 10 not). Out of sample that falls to 45%. Most of the in-sample gain is the weights fitting the data.
- **It costs classic controls.** On round 2b's pooled panels, the doing/allowing and luck controls, both known human effects, are no longer confirmed: 2 of 5 reproduce instead of 4.

## The weights

Each model's weight is max(0, average of its raw correlation with the human gaps on OffTheRails and on MoCa).

| Judge model (persona) | r, OffTheRails | r, MoCa | Weight | Share of the panel |
|---|---|---|---|---|
| Haiku | 0.39 | 0.34 | 0.367 | 40% |
| Opus | 0.45 | 0.25 | 0.348 | 38% |
| Sonnet | 0.40 | −0.01 | 0.198 | 22% |

**Why it can't fix the flips.**
- With these shares, a gap needs Haiku and Opus to agree. Any pair of models without both of them carries less than two-thirds of the weight, so Sonnet's vote never decides.
- Haiku is the dissenter in 8 of the 10 verdicts that split two to one (`reports/Ceiling abstention test.md`). Giving it 40% of the weight restores its veto.
- **The human data give no reason to down-weight Haiku.** It tracks people as well as the others on OffTheRails and best of the three on MoCa. The only model they single out is Sonnet, on MoCa, and Sonnet isn't the one causing the flips.

**Out of sample, the weights change a lot with the data:**
- **From OffTheRails alone,** the three models are nearly equal (0.39, 0.40, 0.45). On MoCa the weighted rule then behaves almost like two-thirds: 14 confirmed, 8 not backed, against 15 and 10.
- **From MoCa alone,** Sonnet gets 0 and drops out. On OffTheRails the panel is then Haiku and Opus, and both must agree: 17 confirmed, 9 not backed, against 18 and 10.

## Human data in detail

| Panel | Rule | Gaps confirmed | ... that people show | ... where people show none | Share people back |
|---|---|---|---|---|---|
| Claude ×3, with personas (rounds 2 and 2b) | pilot | 22 | 12 | 10 | 55% |
| | two-thirds | 33 | 13 | 20 | 39% |
| | weighted, out of sample | 31 | 14 | 17 | 45% |
| | weighted, in sample (optimistic) | 23 | 13 | 10 | 57% |
| Claude ×3, plain | pilot | 27 | 10 | 16 | 37% |
| | two-thirds | 34 | 13 | 20 | 38% |
| | weighted, out of sample | 33 | 11 | 21 | 33% |
| Claude ×4, plain (the pilot's panel) | pilot = two-thirds | 38 | 12 | 25 | 32% |
| | weighted, out of sample | 38 | 13 | 24 | 34% |

*OffTheRails (60 contrasts) and MoCa (85 pairs) together. "Out of sample": MoCa-based weights score OffTheRails, and OffTheRails-based weights score MoCa.*

**For the plain panels, weighting doesn't help.** For the plain three-model panel it is worse than either rule.

## The benchmark's panels under the weights

- **Pilot (four plain models; Fable gets the largest weight, 0.44):**
  - No verdict changes; two prediction scores move, by 0.01 and 0.03.
  - The author order is unchanged.
- **Rounds 2 and 2b (three persona models):**
  - Verdicts close to the threshold move both ways. Haiku's knowledge pair in round 2 loses its gap (0.67 → 0.46), and Haiku's luck pair gains one (−0.47 → −0.55).
  - Three authored pairs and two classic controls lose their confirmation in round 2b, each because Haiku dissents.
  - Opus's mean prediction score in round 2b panel 2 falls from 0.95 to 0.83.
- **Round 2c and the pilot's persona panel were not rescored.** They need a persona weight for Fable, which would only have been collected if the rule had passed.

## What this leaves

Three replacements for the agreement rule have now been tested on the same data:
- the two-thirds rule, adopted on 24 November;
- ceiling abstention, rejected;
- weighting by tracking people, rejected.

None gives both stable verdicts and verdicts people back:

| Rule | Expected score changes in a rerun (round 2b, panel 1) | Persona panel: share of confirmed gaps people back |
|---|---|---|
| Pilot (three quarters) | 5.7 | 55% |
| Two-thirds (current) | 1.7 | 39% |
| Ceiling abstention | 5.7 | 41% |
| Weighted, out of sample | 5.7 | 45% |

**Rule changes on these data look exhausted.**
- The flips come from one model, Haiku, that often sees no gap the other two see.
- The human data don't show that Haiku is wrong to do so.
- So there's no principled way to overrule it only when it's wrong.

**More ratings help stability under any rule.** Round 2c already uses 10 per model and version. At that level (round 2b's two panels pooled), the pilot rule still leaves an expected 2.6 changes per rerun. Beyond that, the human survey remains the only test that doesn't rest on model judges.

## Rerun

```bash
python3 pipeline/test_judge_weights.py --moral-evals <clone of cicl-stanford/moral-evals> --moca <clone of cicl-stanford/moca>
```

It takes about 12 minutes. It rescores into a temporary folder and leaves the published `out/` folders untouched.
