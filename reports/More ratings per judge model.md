# More ratings per judge model: round 2c judged twice, and the four-model panel checked against people

*26 November 2026, at the owner's request ("go ahead with more ratings per judge model"). The measures and the criteria were committed before any new judge ran (commit 16aeb6f, `pipeline/round2/analyse_c_panels.py`). Numbers are in `reports/round2c_panels_numbers.json` and `reports/calibration_numbers_persona4.json`, rebuilt by that script. Pooled scores are in `out/round2c_pooled/`, `reports/shared_pool_round2c_pooled_numbers.json` and `reports/summary_round2c_pooled_numbers.json`.*

## Bottom line

A second, independent 80-judge panel rejudged round 2c with new personas and new batch orders. Pooled with the first, that gives 20 ratings per model and version instead of 10.

**By the criteria set in advance, 20 ratings do not become the standard, because the stability gain is too small:**

| Criterion (fixed in advance) | Needed | Result |
|---|---|---|
| C1. Expected score changes per rerun, 20 ratings against 10 | at most half | 0.7 against 1.0 of 36 authored pairs ✗ |
| C2. On human data, the share of confirmed gaps that people back, 10 judges per model against 5 | at most 5 points lower | 44% against 41% ✓ |

**But the actual rerun was less stable than the resampling predicted, and that's a reason to reconsider:**

- Between the two real panels, 3 of 36 authored pairs changed score by more than 0.25, against the 1.0 that judge-level resampling of panel 1 expected.
- The panels differ by a bit more than sampling noise: noise ratio 1.26.
- The second panel also confirmed a gap on a null control ("weekday", −0.58, all four models agreeing). Pooled, it is back under the 0.5 bar.

So the criterion I set was based on an estimate that, here, understates how much a rerun moves.

**Whatever the outcome, round 2c's headline numbers move to the pooled panel,** as fixed in advance:

| Author | Summary | Composite | Shared-pool score | Own-pair prediction |
|---|---|---|---|---|
| Opus | **77.0** | **81.5** | 72.5 | 0.94 |
| Fable | 73.6 | 72.0 | **75.2** | 0.79 |
| Sonnet | 70.0 | 77.5 | 62.5 | **0.97** |
| Haiku | 63.8 | 70.1 | 57.5 | 0.77 |

*Composite, shared-pool and summary on 0–100; own-pair prediction on 0–1.*

- **The order is the same as with one panel:** Opus, Fable, Sonnet, Haiku. Opus is first in 96% of combined draws, but still not clearly ahead of Fable.
- **Pooling settles one comparison.** Fable is now clearly ahead of Sonnet on the summary, with a 95% interval of +0.3 to +10.4. With one panel it wasn't.

**The four-model persona panel that round 2c uses has now been checked against people,** after Fable's 10 persona judges ran on the public data. With all four models (3 of 4 must agree), 42% of the gaps it confirms are backed by people. That's better than the plain four-model panel (32%) and the three-model persona panel under two-thirds (39%), but short of the three-model persona panel under the pilot rule (55%).

## What was run

- **Round 2c, panel 2** (run `round2c-p2`):
  - 80 persona judges: Fable, Opus, Sonnet and Haiku, 10 repeats × 2 arms each, on the same 46 items as panel 1.
  - New seed (20261129) and new personas; none repeats a panel-1 persona.
  - Manifest: `pipeline/round2/judge_batches_c_p2.json`. Answers: `pipeline/round2/raw/judges_c_p2/`.
  - Provenance (`pipeline/round2/raw/provenance_c_p2.json`):
    - All 80 were served the requested model, read only their own file before writing, and wrote only their own answers.
    - One Haiku judge corrected its own answer file twice, which the rule allows.
    - Eleven Haiku judges made one session-tool call after writing (sending a message, starting a session, interrupting a session, or a hand-back). These were blocked or harmless, and none wrote anything else.
- **Fable's persona judges on the human data:**
  - 10 judges on calibration batches b31–b40, with that batch's persona and the prompt the other persona judges had.
  - All 10 were clean. Answers: `pipeline/calibration/answers_persona/fable/`; provenance in `pipeline/calibration/provenance_persona.json`.
- **Scoring:**
  - Current rules. With four judge models, two-thirds and three-quarters both need 3 of 4.
  - The same audits as panel 1.
  - Pooled panel: `score.py --run round2c,round2c-p2`.

## Stability

**Panel 1 against panel 2** (46 items):
- Effect correlation 0.979; mean absolute difference 0.18 points; noise ratio 1.26.
- Three verdicts change, two of them on authored pairs:
  - Sonnet's avoidable-harm pairs 1 and 3: +0.88 and +0.75 in panel 1, +0.45 and +0.40 in panel 2. They drop just under the 0.5 bar, so the verdict goes from "A higher, small" to "no difference" and the prediction score falls from 1.0 to 0. Pooled, they're confirmed (+0.66, +0.57).
  - The null control "weekday": −0.07 in panel 1, −0.58 with all four models agreeing in panel 2, which is a false confirmation. Pooled it's −0.32, under the bar.
- One more authored score changes by more than 0.25: Fable's parcel pair (+2.20, then +1.80; the prediction score rises from 0.53 to 0.80 as the gap shrinks toward the predicted "small").
- **Sonnet's composite swings with those two pairs:** 76.1 in panel 1, 69.5 in panel 2, 77.5 pooled. No other author moves by more than 2.5 points.

**Judge-level resampling** (300 resamples):

| | Panel 1 (10 ratings) | Pooled (20 ratings) |
|---|---|---|
| Expected authored score changes in a rerun | 1.0 | 0.7 |
| Spread of Opus's mean prediction score | 0.033 | 0.020 |
| Spread of Haiku's | 0.063 | 0.042 |
| Spread of Fable's | 0.039 | 0.034 |
| Spread of Sonnet's | 0.062 | 0.062 |
| First on own-pair prediction | Sonnet 50%, Opus 48% | Sonnet 60%, Opus 40% |

**What this shows:**
- **The four-model panel at 10 ratings is already much steadier than the three-model panels were.** The comparable figure for round 2b's panel 1 under two-thirds was 1.7 of 27 pairs, and under the pilot rule 5.7. Most of the gain came from adding a fourth judge model and going to 10 ratings, not from this doubling.
- **Resampling within one panel underestimates a real rerun here:** 1.0 expected against 3 actual. The noise ratio above 1 suggests each panel's own personas and batch orders add variation that resampling inside a panel can't see. In round 2b, with three models, the resampling had matched the real rerun.

## The four-model persona panel on human data

| Panel | Rule | Gaps confirmed | ... that people show | ... where people show none | Share people back |
|---|---|---|---|---|---|
| Claude ×4, with personas (round 2c's panel) | 3 of 4 | 33 | 14 | 17 | **42%** |
| Claude ×3, with personas (rounds 2 and 2b) | pilot rule (3 of 3) | 22 | 12 | 10 | 55% |
| | two-thirds (2 of 3) | 33 | 13 | 20 | 39% |
| Claude ×4, plain (the pilot's panel) | 3 of 4 | 38 | 12 | 25 | 32% |

*OffTheRails (60 contrasts) and MoCa (85 pairs) together.*

- **By dataset:**
  - OffTheRails: 17 confirmed, 8 backed, 8 not, 1 in the wrong direction.
  - MoCa: 16 confirmed, 6 backed, 9 not, 1 in the wrong direction.
- **Fable's persona judges track people about as well as the others:** a correlation of 0.38 with the human gaps on OffTheRails and 0.31 on MoCa. The other three persona models score 0.39–0.45 on OffTheRails and −0.01 to 0.34 on MoCa.
- **More judges don't make it worse.** In 20 halves of 5 judges per model, the share people back averaged 41%. With all 10 judges (same settings) it's 44%.
  - **Deviation from the committed plan:** a random 5 of 10 calibration judges often leaves a story without a rating at some level, and the analysis can't run. So I redrew the halves until every story, condition and MoCa pair was covered, and added an option to the calibration analysis that lets an empty cell give a missing value in the reliability statistics only.
  - The redrawn halves are therefore balanced subsets, not unrestricted random ones; about 1.7 million draws were rejected to find 20.
  - The full-panel numbers are unaffected. The published calibration outputs are byte-for-byte unchanged without the option.

## Round 2c, pooled (the new headline)

**Shared-pool score** (target: both panels' gaps pooled, as the definition says):

| Predictor | Score | Mean error on others' items |
|---|---|---|
| Fable | 75.2 | 0.37 |
| Opus | 72.5 | 0.41 |
| Sonnet | 62.5 | 0.56 |
| Haiku | 57.5 | 0.64 |

**Paired comparisons on the 28 items neither predictor wrote:**

| Comparison | p |
|---|---|
| Fable − Opus | 0.53 (a tie) |
| Opus − Sonnet | 0.02 |
| Fable − Haiku | 0.0001 |
| Opus − Haiku | 0.04 |
| Fable − Sonnet | 0.09 |

**Summary score** (half composite, half shared pool):

| Comparison | Difference | 95% interval | Clear? |
|---|---|---|---|
| Opus − Fable | +3.4 | −0.4 to +6.8 | no, just |
| Opus − Sonnet | +7.0 | +4.0 to +12.7 | yes |
| Opus − Haiku | +13.2 | +7.6 to +18.4 | yes |
| Fable − Sonnet | +3.6 | +0.3 to +10.4 | yes (not with one panel) |
| Fable − Haiku | +9.8 | +3.5 to +16.6 | yes |
| Sonnet − Haiku | +6.2 | −0.8 to +11.0 | no |

**Against panel 1 alone:**
- Opus's composite rises from 80.7 to 81.5, and Sonnet's from 76.1 to 77.5. Both come through own-pair prediction: Opus 0.91 → 0.94, Sonnet 0.94 → 0.97.
- Fable's shared-pool score rises from 72.2 to 75.2, and Opus's from 69.9 to 72.5. The pooled gaps are less noisy, so both good predictors look better.

## What this means

1. **The current design (four judge models, 10 ratings per model and version) is already fairly stable.** By the measure set in advance, doubling it doesn't pay for itself.
2. **A real rerun moved more than that measure predicted.** It flipped two of Sonnet's pairs and confirmed a gap on a null control. Pooling two panels fixed both.
3. **So whether to pay for 20 ratings is a judgement about cost.**
   - Twice the judges per round buys protection against a single panel's bad draw.
   - That protection matters most when an author's pairs sit near the 0.5 bar, as Sonnet's avoidable-harm pairs do.
   - By the committed criterion the answer is no. I'd keep that, but flag it as a close call.
4. **The panel round 2c uses has been checked against people for the first time,** and it is middling: 42% of its confirmed gaps are backed by people. That's better than the plain panel and the three-model two-thirds panel, worse than the three-model pilot rule. The human survey remains the only way to know how it does on the benchmark's own pairs.

## Rerun

```bash
python3 pipeline/round2/build.py judges --tag c --panel 2 --out DIR --models fable opus sonnet haiku --repeats 10 --seed 20261129 --run-id round2c-p2
```

```bash
python3 pipeline/round2/build.py check --tag c --panel 2 --transcripts DIR
```

```bash
python3 pipeline/round2/build.py ingest --tag c --panel 2 --judges pipeline/round2/raw/judges_c_p2 --run-id round2c-p2
```

```bash
python3 score.py --vignettes round2/vignettes_c.json --run round2c-p2 --audit-run main,round2,round2b,round2c --out out/round2c_p2 --no-report
```

```bash
python3 score.py --vignettes round2/vignettes_c.json --run round2c,round2c-p2 --audit-run main,round2,round2b,round2c --out out/round2c_pooled --no-report
```

```bash
python3 pipeline/round2/analyse_c_panels.py --moral-evals <clone of cicl-stanford/moral-evals> --moca <clone of cicl-stanford/moca>
```

```bash
python3 pipeline/shared_pool.py score --vignettes round2/vignettes_c.json --runs round2c,round2c-p2 --manifest pipeline/round2/shared_pool_manifest_c.json --answers pipeline/round2/raw/shared_pool_c --provenance pipeline/round2/raw/provenance_pool_c.json --out reports/shared_pool_round2c_pooled_numbers.json
```

```bash
python3 pipeline/summary_score.py --results out/round2c_pooled/results.json --vignettes round2/vignettes_c.json --runs round2c,round2c-p2 --manifest pipeline/round2/shared_pool_manifest_c.json --answers pipeline/round2/raw/shared_pool_c --provenance pipeline/round2/raw/provenance_pool_c.json --shared reports/shared_pool_round2c_pooled_numbers.json --out reports/summary_round2c_pooled_numbers.json
```
