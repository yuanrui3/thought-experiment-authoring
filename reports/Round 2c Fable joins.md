# Round 2c: Fable joins, and all four authors are scored on one panel

*26 November 2026. Pairs in `round2/vignettes_c.json`; run `round2c` in `judgments.csv` and `audits.csv`; scores in `out/round2c/`. Composite and own-pair numbers are in `reports/round2c_numbers.json`, rebuilt by `pipeline/round2/analyse_c.py`. Shared-pool numbers are in `reports/shared_pool_round2c_numbers.json`, rebuilt by `pipeline/shared_pool.py score`. All four authors' shared-pool predictions were committed before any judging (commit 9bf8007). Current rules throughout: the distance prediction score and the two-thirds agreement rule, which with four judge models means 3 of 4.*

## Bottom line

Fable wrote nine pairs on the three contested factors, the same brief and the same number as the other three authors. All 36 authored pairs and the 10 controls were then judged together by one persona panel with all four Claude models as judges.

**The two scores disagree about Fable:**

| Author | Composite (own 9 pairs) | Own-pair prediction score | Shared-pool score |
|---|---|---|---|
| Opus | **80.7** | 0.91 | 69.9 |
| Sonnet | 76.1 | **0.94** | 62.0 |
| Fable | 70.7 | 0.75 | **72.2** |
| Haiku | 70.0 | 0.77 | 57.0 |

*Composite: 0–100, the benchmark's main score. Own-pair prediction score: 0–1, how close each pair's measured gap came to its author's predicted size. Shared-pool score: 0–100, how well the author predicted, in points, the gaps of pairs it didn't write and of the controls (`reports/Shared-pool prediction score.md`).*

- **As a pair designer, Fable is third on the composite and last on prediction.**
  - Behind Sonnet, the prediction gap is significant: p = 0.04 in a permutation test within factors.
  - Fable is never first in 300 judge-level resamples, and last in 68%.
  - Against Opus (p = 0.19) and Haiku (p = 0.92), the differences are within noise.
- **As a predictor of readers, Fable is first,** level with Opus.
  - On the 28 items neither of them wrote, Fable's mean error is 0.016 points smaller than Opus's (p = 0.77). That is a tie.
  - Both are clearly ahead of Haiku. Opus is again clearly ahead of Sonnet (p = 0.02), as in round 2b.
- **Where Fable lost points:**
  - It predicted "small" for its three knowledge pairs, and all three came out large (1.8 to 1.9 points). All four authors predicted "small" for every knowledge pair, so this miss is shared, not Fable's alone.
  - One luck pair hit the scale's ceiling and showed no gap.
  - One luck pair carried a confound the auditors caught.
  - Its three avoidable-harm pairs were the best set of the round: all three on target, composites 85 to 93.
- **The panel itself held up:**
  - The 37 items carried over from round 2b reproduce: effect correlation 0.975 and no verdict changes.
  - All 5 null pairs stay null. 4 of 5 classic controls reproduce; the avoidable-harm control fails, as in every run.

## What was run

- **Authors:**
  - Fable wrote three pairs from the round-2 brief, then six more from the round-2b brief. That is the same two steps the others took, with the same wording.
  - It saw no results from earlier rounds.
  - Provenance: `pipeline/round2/raw/provenance_c.json`.
- **Shared-pool predictions:**
  - Each of the four authors, in a fresh context, predicted the gap in points for all 46 items under neutral codes. They were not told which pairs were their own.
  - All four were committed before judging started.
- **Judges:**
  - 80 persona judges: Haiku, Sonnet, Opus and Fable, 10 repeats × 2 arms each, so 10 ratings per model and version.
  - Each saw one version of every item, 46 per batch, with a new seed (`pipeline/round2/judge_batches_c.json`).
  - 3,680 ratings in all. Comprehension questions were right 99.3% of the time (Haiku 97.5%, the others at least 99.8%).
- **Auditors:**
  - Haiku, Sonnet and Opus each audited Fable's nine pairs.
  - Fable audited the 27 other authored pairs and the three new-factor classic controls (`pipeline/round2/audit_batches_c.json`).
  - Scoring uses every audit a pair has from rounds 2, 2b and 2c.
- **Provenance** (`pipeline/round2/raw/provenance_c.json`):
  - All 80 judges and 4 auditors were served the requested model, read only their own file before writing, and wrote only their own answer file.
  - Nine Haiku judges made one or two further calls after writing. Five sent a session message, two read product documentation, one listed sessions and one called a hand-back tool. None wrote anything, so under the committed rule their answers stand.

## Authors on their own pairs

| Author | Composite | Prediction score | Pairs showing a gap | Mean confound (0–3) | Mean originality (0–2) | Avoidable harm | Knowledge and causation | Luck and wrongness |
|---|---|---|---|---|---|---|---|---|
| Opus | 80.7 | 0.91 | 9/9 | 0.67 | 1.44 | 0.99 | 0.79 | 0.96 |
| Sonnet | 76.1 | 0.94 | 9/9 | 1.22 | 1.33 | 1.00 | 0.81 | 1.00 |
| Fable | 70.7 | 0.75 | 8/9 | 1.00 | 1.33 | 1.00 | 0.75 | 0.51 |
| Haiku | 70.0 | 0.77 | 8/9 | 1.22 | 1.44 | 0.89 | 0.99 | 0.43 |

*The last three columns are mean prediction scores by factor.*

**Fable's nine pairs:**

| Pair | Predicted | Measured gap (A − B) | Verdict | Prediction score | Confound | Composite |
|---|---|---|---|---|---|---|
| Greenhouse vent and the heater (avoidable harm) | A higher, large | +2.42 | A higher, large | 1.00 | 1 | 85.0 |
| Late lift to the ferry (avoidable harm) | A higher, large | +2.88 | A higher, large | 1.00 | 0 | 93.3 |
| Skipped Friday backup (avoidable harm) | A higher, large | +2.20 | A higher, large | 1.00 | 1 | 85.0 |
| Heater in the village hall kitchen (knowledge) | A higher, small | +1.90 | A higher, large | 0.73 | 1 | 67.5 |
| Bicycle on the stairwell railing (knowledge) | A higher, small | +1.80 | A higher, large | 0.80 | 1 | 70.3 |
| Draft saved in the Ready folder (knowledge) | A higher, small | +1.92 | A higher, large | 0.72 | 1 | 67.0 |
| Tiles thrown onto the side path (luck) | A higher, small | +0.32 | no difference | 0.00 | 1 | 38.3 |
| Dog let off the lead (luck) | A higher, small | +0.88 | A higher, small | 1.00 | 1 | 78.3 |
| Parcel left on the doorstep (luck) | A higher, small | +2.20 | A higher, large | 0.53 | 2 | 51.3 |

*Ratings are on a 1–7 scale. All four judge models agreed in sign on every one of Fable's pairs.*

**What the auditors said about Fable's pairs** (Haiku, Sonnet and Opus; the pair's grade is the median of the three):

- **Knowledge pairs:**
  - All three auditors noted that version B adds "no sign (or notice, or screen) mentioned the rule". That implies the institution failed to warn, a rival cause that exists only in B.
  - Opus added that knowing the rule also means foreseeing the harm, so foreseeability changes with knowledge.
  - Haiku called two of the three re-skins of the first design (originality 0). Sonnet and Opus gave them 1 or 2.
- **Parcel pair** (luck):
  - A thief who takes the parcel appears only in version A: a second wrongdoer and an intervening cause. Haiku graded it 3 (severe), Opus 2, Sonnet 1.
  - Version B also ends with a benefit ("able to follow every conversation from then on"), not just the absence of harm.
  - It is Fable's only pair to fail the confound gate.
- **Tiles pair** (luck):
  - Sonnet's auditor, who saw no ratings, predicted exactly this: throwing tiles blindly where someone is known to walk "is so reckless that wrongness may hit the ceiling in both versions". The two versions averaged 6.4 and 6.1.
- **Dog pair** (luck): version B adds that the dog came back when called and was put back on the lead, a cue that the risk was controllable.
- **Avoidable-harm pairs:**
  - Confound 0 or 1.
  - In the greenhouse pair, B's heater failing that evening is a second cause.
  - All three auditors noted that "responsible" can be read as blame for the broken instruction, which is the same in both versions.

**Two things the own-pair prediction score does here:**

1. **On knowledge pairs it rewards weaker manipulations.**
   - Every author predicted "small" for all three of its knowledge pairs.
   - Haiku's pairs produced gaps of 1.3 to 1.6 and scored about 1.0.
   - Fable's, Opus's and Sonnet's produced 1.65 to 1.98 and scored 0.68 to 0.90.
   - The authors share the same misjudgement (the point-prediction test found it too); the score separates them by how strong their manipulation happened to be.
2. **It punishes ceiling effects hard.** The tiles pair scores 0 because both versions sit near the top of the scale. Fable didn't anticipate that; one of the auditors did.

**How sure the order is:**

- In 300 judge-level resamples (judges resampled within each model, every gap and score recomputed), Sonnet is first 52% of the time, Opus 44%, Haiku 4%, Fable 0%. Fable is last 68% of the time.
- Permutation test of prediction scores, shuffling authors among the 12 pairs of each factor:

  | Comparison | Difference | p |
  |---|---|---|
  | Fable − Sonnet | −0.18 | 0.04 |
  | Fable − Opus | −0.16 | 0.19 |
  | Haiku − Sonnet | −0.17 | 0.21 |
  | Haiku − Opus | −0.14 | 0.26 |
  | Opus − Sonnet | −0.02 | 0.39 |
  | Fable − Haiku | −0.02 | 0.92 |

  With nine pairs per author, only the Fable–Sonnet gap clears p < 0.05.

## The shared-pool score

| Predictor | Shared-pool score | Mean error on others' items (37) | Mean error on own items (9) | Correlation with measured gaps (all 46) | Mean signed error |
|---|---|---|---|---|---|
| Fable | **72.2** (sd 2.6) | **0.42** | 0.56 | **0.90** | −0.29 |
| Opus | 69.9 (sd 2.9) | 0.45 | 0.59 | 0.90 | −0.30 |
| Sonnet | 62.0 (sd 2.9) | 0.57 | 0.51 | 0.87 | −0.39 |
| Haiku | 57.0 (sd 2.2) | 0.66 | 0.77 | 0.82 | −0.21 |

*Errors are in points on the 1–7 scale. sd is the spread over 2,000 judge-level resamples.*

**Order over the 2,000 resamples:**
- Fable, Opus, Sonnet, Haiku: 93%.
- Opus, Fable, Sonnet, Haiku: 7%.

**Paired comparisons on the 28 items neither predictor wrote** (sign-flip test):

| Comparison | Difference in mean error | p |
|---|---|---|
| Fable − Haiku | −0.21 | 0.006 |
| Opus − Sonnet | −0.16 | 0.02 |
| Haiku − Opus | +0.15 | 0.07 |
| Fable − Sonnet | −0.10 | 0.15 |
| Fable − Opus | −0.02 | 0.77 |
| Haiku − Sonnet | −0.02 | 0.88 |

- **Fable and Opus are the two best predictors, and can't be told apart.** The resamples only vary the judges, not the items, so the 93% overstates how settled the order is. The paired test on items is the fairer comparison, and it calls Fable and Opus a tie.
- **Opus beats Sonnet again.** It did in round 2b too (p = 0.009 in the point-prediction test), so this is the most stable finding about prediction so far.
- **Every predictor under-estimated the gaps,** by 0.2 to 0.4 points on average. This panel, with Fable among the judges, gave bigger gaps than the three-model panels of round 2b (by 0.12 on the shared items and 0.14 on authored pairs). The task text described earlier rounds' range, and those were judged by three models.
- **Authors don't predict their own pairs better.** Fable, Opus and Haiku did worse on their own nine pairs than on others' items; only Sonnet did better.
  - This isn't like-for-like: own items are all contested-factor pairs, while others' items include the five null controls, which are easy to predict.
  - Still, writing a pair gave no visible advantage in predicting its gap.

## Is the panel the same as before?

- **The 37 items carried over from round 2b** (27 authored pairs and 10 controls), against the two round-2b panels pooled:
  - Effect correlation 0.975, mean absolute difference 0.22 points.
  - No verdict changes, and no prediction score changes by more than 0.25.
  - The noise ratio is 1.42. Above 1 is expected: this panel has a fourth judge model and 46-item batches instead of 37, so it isn't a pure test-retest.
- **The other authors' scores dropped a little:**
  - Opus 83.2 → 80.7, Sonnet 80.6 → 76.1, Haiku 70.4 → 70.0.
  - Larger gaps pushed some "small" predictions into "large".
  - Fable's audits raised three of Sonnet's pairs one confound grade (see Caveats).
- **Judge models:**
  - Haiku's judges gave much smaller gaps than the other three: a mean signed gap of 0.90 on authored pairs, against 1.34 to 1.37, and twice the within-version spread.
  - Fable's judges behaved like Opus's and Sonnet's.
- **No consistent home advantage.**
  - Compared with the other three judge models, Fable's judges gave Fable's pairs +0.17 points and Opus's pairs +0.34.
  - Opus's judges gave Opus's pairs +0.30 and Fable's +0.38.
  - Sonnet's and Haiku's judges did not favour their own model's pairs.
- **Controls:**
  - The 5 null pairs all stay null; the largest gap is 0.28.
  - 4 of 5 classic controls reproduce. The avoidable-harm control shows nothing (−0.05, only 2 of 4 models agree in sign), as in every run so far.

## What this means

1. **Fable's earlier lead doesn't carry over to contested factors.** On the pilot it led narrowly under the persona panel (75.1 against Sonnet's 73.3). Here, under the same kind of panel with all four judge models, it is third on the composite. Its losses come from one confound, one ceiling pair and a size misjudgement it shares with every author.
2. **On predicting readers, Fable and Opus are the best,** as they were at predicting people on public data (`reports/Authors predicting people.md`):
   - on human data, Fable and Opus were the two best, about equal;
   - on the round-2b pool, where Fable was missing, Opus was clearly best;
   - on this round's pool they tie for first.
3. **The two scores measure different things, as option B intended.**
   - Sonnet designs pairs whose size it calls well: it predicts "small" and lands there. But as a general predictor it is third.
   - Fable is the reverse.
   - Folding them into one number would hide that, so they stay side by side.
4. **The own-pair prediction score has a known weakness on factors where every author misjudges the size the same way:** it then ranks authors by how strong their manipulation happened to be. The shared-pool score doesn't have that problem, because every predictor is scored on the same items. This is a reason to give the shared-pool score at least equal weight in any summary.
5. **Haiku is last on the composite and on the shared pool,** and level with Fable on own-pair prediction (p = 0.92). Opus is in the top two on all three measures.

## Caveats

- **The judges are models, not people.** Fable is now both an author and a judge; there is no sign it favours its own pairs, but the panel is still four Claude models.
- **The audits aren't symmetric.**
  - The other authors' pairs have four audits, and the grade is the upper median: Haiku, Sonnet and Opus from round 2 or 2b, plus Fable's.
  - Fable's pairs have three, and the grade is the median. Fable doesn't audit its own pairs here, while the earlier rounds had each author audit its own.
  - Fable's audit raised three of Sonnet's pairs from confound 0 to 1 (two pairs) or 1 to 2 (one pair). That costs Sonnet 2.8 composite points: 78.8 without it.
  - Opus's and Haiku's scores are unchanged by it.
  - The order doesn't change.
- **Nine pairs per author.** Only one own-pair difference clears p < 0.05, and it would not survive a correction for six comparisons.
- **One shared-pool prediction per model per item.** A rerun of the same predictor would vary, and that spread wasn't measured.
- **The other authors' pairs have now been judged by four panels.** This run is the only one with all four authors on the same panel, so it is the one to compare authors on. The round-2b numbers remain the reference for the three-model panel.

## Rerun

```bash
python3 score.py --vignettes round2/vignettes_c.json --run round2c --audit-run main,round2,round2b,round2c --out out/round2c --no-report
```

```bash
python3 pipeline/round2/analyse_c.py
```

```bash
python3 pipeline/shared_pool.py score --vignettes round2/vignettes_c.json --runs round2c --manifest pipeline/round2/shared_pool_manifest_c.json --answers pipeline/round2/raw/shared_pool_c --provenance pipeline/round2/raw/provenance_pool_c.json --out reports/shared_pool_round2c_numbers.json
```

The builder steps (brief, assemble, judges, auditors, check, ingest) are listed at the top of `pipeline/round2/build.py` under "With --tag c".
