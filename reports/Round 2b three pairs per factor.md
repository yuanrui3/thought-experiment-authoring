# Round 2b: three pairs per author per factor

*22 November 2026. Pairs in `round2/vignettes_b.json`; judgments and audits are run `round2b` in `judgments.csv` and `audits.csv`; scores in `out/round2b/`, from `python3 score.py --vignettes round2/vignettes_b.json --run round2b --audit-run main,round2,round2b --out out/round2b --no-report`. Every number below is rebuilt by `python3 pipeline/round2/analyse_b.py` into `reports/round2b_numbers.json`. Fable is missing (usage limit until 26 November).*

## Bottom line

- **Haiku is last again, and Opus and Sonnet can't be told apart.** With nine pairs each on the three new factors:

  | Author | Prediction score | Composite |
  |---|---|---|
  | Opus | 0.98 | 83.4 |
  | Sonnet | 0.88 | 76.5 |
  | Haiku | 0.66 | 65.5 |

  - A permutation test that shuffles authors within each factor separates Haiku from Opus (p = 0.04).
  - It does not separate Haiku from Sonnet (p = 0.20) or Sonnet from Opus (p = 0.80).
  - Authorship explains 18% of the spread in pair scores.
- **Three pairs per factor did what they were meant to, within one run.** In simulated reruns, the spread of an author's mean fell from about 0.18 to about 0.11.
- **But a second run of the panel moves scores far more than that.**
  - The nine round-2 pairs were judged again here, by a new panel of the same design with new personas and a different batch mix.
  - Their mean prediction score went from 0.44 to 0.73.
  - 5 of the 9 changed by more than a quarter point, four of them from 0 to full credit or back. Round 2's simulation predicted about 1.6 such changes.
  - The run itself is the largest source of error, and resampling ratings within a run doesn't see it.
- **Round 2's claim that the new factors are harder doesn't hold up.**
  - It rested on a comparison across panel runs. Run to run, the same pairs moved by about as much as the claimed difference.
  - In this run, Opus and Sonnet get full marks on 15 of their 18 pairs. That is back near a ceiling for the two stronger authors.

## What was run

- **Authors.** Haiku, Sonnet and Opus each wrote two more pairs per new factor (18 new pairs), from the round-2 brief.
  - The brief changed only to ask for six pairs and to show each author its own three round-2 pairs (texts and questions only), with an instruction to use different settings.
  - Every author read only its brief and wrote only its answer file.
- **Judges.** A persona panel of the same design as round 2: Haiku, Sonnet and Opus × 5 repeats × 2 arms = 30 judges.
  - The personas were drawn with a new seed.
  - Each judge rated one version of all 37 pairs: the 27 authored pairs on the new factors, the 5 classic controls and the 5 nulls. That makes 1,110 judgments.
  - Two judges made a harmless call after writing their answers: a tool lookup, and a "done" message to this session.
- **Auditors.** Haiku, Sonnet and Opus audited the 18 new pairs with the pilot's audit prompt, word for word. The round-2 pairs keep their round-2 audits.
- **Scoring.** Unchanged.

## Authors

| Author | Avoidable harm | Knowing the rule | Luck and wrongness | Demonstrated | Full marks | Confound severity (mean) |
|---|---|---|---|---|---|---|
| Opus | 1.00, 1.00, 1.00 | 1.00, 0.84, 1.00 | 1.00, 1.00, 1.00 | 9/9 | 8/9 | 0.67 |
| Sonnet | 1.00, 1.00, 1.00 | 1.00, 1.00, 0.93 | 0, 1.00, 1.00 | 8/9 | 7/9 | 0.89 |
| Haiku | 0.58, 0.89, 0 | 1.00, 1.00, 1.00 | 0, 0.49, 0.98 | 7/9 | 3/9 | 1.22 |

*Prediction scores, in order: the round-2 pair, then the two new ones.*

- **Haiku loses on size.**
  - Its avoidable-harm pairs overshoot. All were predicted small; two measured 2.1 and 1.7.
  - It predicted large gaps on two luck pairs that came out small (−0.73 and −1.47).
  - One avoidable-harm pair (bus route and rockfall) isn't confirmed because one judge model disagrees.
- **Opus is the only author to predict large gaps and get them:** +3.07 (café fridge) and +1.93 (airport stop), both on avoidable harm.
- **Sonnet predicted "small" every time** and was right 7 times out of 9. Its one zero is its round-2 babysitter pair, which lost its confirmation in this run.
- **Auditors' grades** (mean confound severity, 0–3) put Opus's pairs cleanest (0.67) and Haiku's least clean (1.22).
  - The main complaint was on knowledge pairs: the "didn't know" version also implies an employer failed to tell the person.
  - All three auditors raised it on one of Haiku's new knowledge pairs, and one auditor raised it on each of Sonnet's.
  - All three graded Opus's new knowledge pairs clean.

## The same nine pairs, judged twice

| Pair | Round 2: gap, verdict, score | Round 2b: gap, verdict, score |
|---|---|---|
| Haiku, sluice gate (avoidable harm) | +2.67, A higher, 0.22 | +2.13, A higher, 0.58 |
| Haiku, solvent room (knowledge) | +0.67, unclear, 0 | +1.00, A higher, **1.00** |
| Haiku, roofer (luck) | −0.47, none, 0 | −0.33, none, 0 |
| Sonnet, greenhouse (avoidable harm) | +0.33, none, 0 | +0.73, A higher, **1.00** |
| Sonnet, circuit (knowledge) | +1.87, A higher, 0.76 | +1.40, A higher, 1.00 |
| Sonnet, babysitter (luck) | −0.93, B higher, 1.00 | −0.40, none, **0** |
| Opus, beehives (avoidable harm) | +1.13, A higher, 1.00 | +1.07, A higher, 1.00 |
| Opus, farm gate (knowledge) | +1.53, A higher, 0.98 | +1.33, A higher, 1.00 |
| Opus, smoke alarm (luck) | +1.40, unclear, 0 | +1.07, A higher, **1.00** |

- **Gaps are stable; verdicts are not.**
  - Across these 9 pairs and the 10 controls, the two runs' gaps correlate 0.91, with a mean difference of 0.31 points.
  - But all three judge models agreed on the direction for 5 of 9 pairs in round 2, and for 9 of 9 here. In this run they agree on 26 of all 27 pairs.
  - Of the four flips on authored pairs, two come from the all-models-agree rule (solvent room, smoke alarm). The other two are gaps crossing the 0.5 line: the greenhouse rose from +0.33 to +0.73, and the babysitter fell from −0.93 to −0.40.
- **By author, on these nine pairs:** Haiku 0.07 → 0.53, Sonnet 0.59 → 0.67, Opus 0.66 → 1.00. The order held; the levels did not.
- **Why this run agrees more, I can't tell.** The personas differ, and so does the batch: 30 of 37 items in a batch were on the three new factors, against 12 of 27 in round 2. Seeing many stories that vary the same detail may make judges more alert to it. That is a context effect people would be exposed to as well.

## Controls

| Control | Round 2 | Round 2b |
|---|---|---|
| The bike lanes (avoidable harm) | +0.20, not reproduced | −0.27, not reproduced |
| The pencil box (knowledge) | +1.47, reproduced | +1.07, reproduced |
| The bath (luck and wrongness) | +0.80, reproduced | +0.93, reproduced |
| Doing vs allowing | +0.93, reproduced | +1.07, **unclear** (one model disagrees) |
| Norm violation | +1.73, reproduced | +1.73, reproduced |
| Nulls | 0 of 5 crossed | 0 of 5 crossed; largest 0.40 |

- **The avoidable-harm control fails again.** The panel's blind spot on intention is consistent.
- **The doing-vs-allowing control fails for the first time in any run,** on the agreement rule, with a gap (+1.07) as large as before.

## How fragile the scores are

Simulated reruns, resampling ratings within each judge-model × version cell as in round 2:

- **Author order:**

  | Order | Share of reruns |
  |---|---|
  | Opus > Sonnet > Haiku | 48% |
  | Sonnet > Opus > Haiku | 27% |
  | Opus > Haiku > Sonnet | 16% |
  | Other orders | 9% |

  Haiku is last in 76% of reruns, and Opus first in 64%.
- **Single pairs:** 11 of the 27 authored pairs keep their score (within 0.25) in fewer than 80% of reruns.
- **This simulation understates real reruns.** On the nine repeated pairs, round 2's version of it predicted about 1.6 score changes; the real second run produced 5.

## What this means

1. **Compare authors only within one run.** A panel run carries its own shift, larger than the noise within it, so a score from one run can't be compared with a score from another. Fable's pairs must be judged in the same run as everyone else's, not added later.
2. **Treat the panel run as a random effect.** Judge the same set with two or more independent panels (new personas, new batch orders) and average them. The spread between runs is the honest error bar, not the bootstrap within a run.
3. **More pairs were needed, but they aren't enough.** They cut within-run noise by about 40%, as expected. The run-to-run shift is not reduced by more pairs, because it moves pairs together.
4. **The ceiling is back for strong authors.** Most pairs land in "small", and "small" is what most authors predict. To separate Opus from Sonnet, the task needs a sharper target: a stated target size the author must hit, or a predicted gap in points scored by distance.
5. **Round 2's "harder factors" finding is withdrawn,** and the round-2 report now says so.

## Judgment calls

1. **Scope.** Only the three new factors got more pairs. The pilot's doing-vs-allowing and norm pairs stay at one per author and weren't judged here, apart from their classic controls.
2. **Authors saw their own earlier pairs.** They were shown texts and questions, but no predictions or results, so they would not repeat a setting. None did.
3. **Everything on the new factors was judged together,** including the round-2 pairs, so an author's three pairs per factor share one run. This also gave the test-retest above.
4. **No scoring change.** The rules are those fixed before the pilot's data, plus the 22 November prediction rule.
