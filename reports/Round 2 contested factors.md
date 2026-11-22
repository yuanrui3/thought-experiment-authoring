# Round 2: three contested factors replace the three easy ones

*22 November 2026. Pairs in `round2/vignettes.json`; judgments are run `round2` in `judgments.csv` and audits are run `round2` in `audits.csv`; scores in `out/round2/`, from `python3 score.py --vignettes round2/vignettes.json --run round2 --audit-run main,round2 --out out/round2 --no-report`. Every number below is rebuilt by `python3 pipeline/round2/analyse.py` into `reports/round2_numbers.json`. Fable is missing from round 2 (usage limit until 26 November); the published pilot results are unchanged.*

## Bottom line

- **The new factors are harder, which was the point.** The same three authors (Haiku, Sonnet, Opus) score a mean prediction score of 0.44 on the new factors. On the pilot's three easy factors they scored 0.72 under the same kind of panel. Full marks drop from 6 of 9 pairs to 2 of 9, and zeros rise from 2 of 9 to 4 of 9. No new factor gives every author full marks; the pilot's intention factor did, under every panel.
- **The author order on the new factors is Opus, Sonnet, Haiku.**

  | Author | Prediction score | Composite |
  |---|---|---|
  | Opus | 0.66 | 71.9 |
  | Sonnet | 0.59 | 61.2 |
  | Haiku | 0.07 | 43.0 |

  That's the same order as the pilot's persona panel for these three authors.
- **But single scores are fragile.** Each author wrote one pair per factor, and each judge model gave 5 ratings per version.
  - In simulated reruns, Opus stays first 88% of the time and Haiku stays last 80%; the full order holds 70% of the time.
  - Even the classic controls that reproduced would fail in 24–47% of reruns.
  - Two real runs of the same panel design, on the 15 pairs reused from the pilot, disagree on 2 verdicts. For one authored pair, the score swings from 0 to full.
- **One new classic control fails, on the panel's known blind spot.** People think a harm the agent could have avoided is more intended. The panel doesn't. On the OffTheRails text used here, people's gap was +0.71 on a 1–5 scale; the panel's is +0.20, not confirmed. Calibration on public human data found the same miss. On the inevitable-harm factor, the panel is a reader that disagrees with people.

## What was run

| | Pilot | Round 2 |
|---|---|---|
| Factors | intention vs accident, doing vs allowing, knowledge vs lucky true belief, moral luck, norm violation and causation | doing vs allowing and norm violation kept (pilot pairs reused unchanged); three new factors (below) |
| Authors | Haiku, Sonnet, Opus, Fable; one pair per factor | Haiku, Sonnet, Opus; one new pair per new factor. The brief is the pilot's, changed only where round 2 differs: the three factors, persona readers, and the distance scoring rule |
| Judges | 4 models × 5 repeats × 2 arms (main panel); persona panel: 3 models | Persona panel as in the pilot's persona run: Haiku, Sonnet, Opus × 5 repeats × 2 arms = 30 judges. Each judge rated one version of all 27 pairs (810 judgments) |
| Auditors | 4 models | 3 models (no Fable), the pilot's audit prompt word for word, on the 9 new pairs and 3 new controls. Reused pairs keep the pilot's audits |
| Scoring | `score.py` | Unchanged, with the current prediction rule |

**The new factors**, each with a classic control anchored to a human result:

| Factor | Question it asks | Classic control | Human result |
|---|---|---|---|
| Inevitable harm | Does a harm count against the agent less if it would have happened anyway? | "The bike lanes": OffTheRails scenario 0, the study's own text; question about intention | Intended more when avoidable: 2.67 vs 1.96 on 1–5 (Fränken, Gandhi et al. 2024) |
| Knowledge and causation | Is someone who breaks a rule more of a cause when they knew the rule? | "The pencil box": MoCa stories 139/141, paraphrased | 88% vs 44% said the hedgehog caused the problem (Nie et al. 2023) |
| Luck and wrongness | Does a bad outcome make the same choice more *wrong*, not just more blameworthy? | "The bath": paraphrase of Kneer & Machery (2019), Study 3 | Wrongness 6.00 vs 5.17 on 1–7 |

Each of these is contested in the sense that matters here: the effect is real in some studies, small or absent in others, and depends on the question asked. Kneer & Machery found that outcomes move punishment more than wrongness, for example.

**Provenance.** All 36 agents (3 authors, 3 auditors, 30 judges) read only their own instructions before writing their answer file. One Sonnet judge then edited its own answer file to change one comprehension answer. I counted that judge (see "Judgment calls").

## The nine new pairs

All nine predictions are "small" (a gap of 0.5 to 1.5 points). "Kept in reruns" is the share of simulated reruns whose score lands within 0.25 of the observed one.

| Pair | Author | Factor | Gap [95% interval] | Models agreeing | Score | Kept in reruns | Auditors' main concern |
|---|---|---|---|---|---|---|---|
| Sluice gate and flooded lane | Haiku | inevitable harm | +2.67 [+2.07, +3.20] | 3/3 | 0.22 | 0.88 | B's overflow ditch reads as a maintenance fault |
| Solvent room door | Haiku | knowledge | +0.67 [+0.20, +1.13] | 2/3 | 0 | 0.84 | B's side-hatch entry implies the employer never told him |
| Roofer without harness | Haiku | luck (B higher) | −0.47 [−1.00, +0.07] | 2/3 | 0 | 0.77 | A shows Hal's skill in catching the gutter |
| Ladder and greenhouse | Sonnet | inevitable harm | +0.33 [−0.13, +0.87] | 2/3 | 0 | 0.96 | B's panel "loose for weeks" implies the owner's neglect |
| Office circuit overload | Sonnet | knowledge | +1.87 [+1.27, +2.47] | 3/3 | 0.76 | 0.86 | B implies the office failed to inform him |
| Babysitter shop trip | Sonnet | luck (B higher) | −0.93 [−1.53, −0.33] | 3/3 | 1.00 | 0.54 | A says "Nothing went wrong" outright |
| Orchard spray and beehives | Opus | inevitable harm | +1.13 [+0.60, +1.67] | 3/3 | 1.00 | 0.92 | B's diseased hives shrink the neighbour's loss |
| Farm side gate | Opus | knowledge | +1.53 [+1.07, +2.00] | 3/3 | 0.98 | 0.96 | none: all three auditors graded it 0 |
| Smoke alarm battery | Opus | luck | +1.40 [+0.80, +1.93] | 2/3 | 0 | 0.68 | only B has Owen replace the battery next morning |

- **Haiku.**
  - Its flood pair overshoots: asked "how much of the flooding was Owen's doing", judges gave it 2.7 points more when the flood was avoidable, far beyond "small".
  - Its other two gaps are not confirmed. On the solvent-room pair, Haiku's own judges rated the knowing version lower (−0.4).
- **Sonnet.**
  - Its circuit pair is solid but larger than predicted.
  - The babysitter pair hits its range, but only just clears the confirmation rule (kept in 54% of reruns).
  - The greenhouse pair shows no gap. It asks how *wrong* leaving the ladder was. Wrongness of a risky act may simply not depend on whether the panel would have blown out anyway.
- **Opus.**
  - Two clean hits: the beehive and farm-gate pairs. The farm gate is the only new pair no auditor faulted.
  - The smoke-alarm gap is real for the Haiku and Opus judges (+2.8, +1.4) but zero for Sonnet's, so it isn't confirmed.
- **Nobody predicted a large gap on a contested factor.** That is a reasonable bet. But it means every author needs a gap that is both modest and confirmed by all three judge models on 5 ratings each: a narrow target.

## Controls

| Control | People | Panel, A vs B (1–7) | Panel gap | Verdict |
|---|---|---|---|---|
| The bike lanes (inevitable harm) | 2.67 vs 1.96 on 1–5 (+0.71) | 1.93 vs 1.73 | +0.20 [−0.20, +0.60] | not reproduced |
| The pencil box (knowledge) | 88% vs 44% "yes, caused" | 4.33 vs 2.87 | +1.47 [+0.87, +2.07] | reproduced |
| The bath (luck and wrongness) | 6.00 vs 5.17 (+0.83) | 6.80 vs 6.00 | +0.80 [+0.47, +1.13] | reproduced, same size |
| Kept from the pilot: doing vs allowing | (see pilot) | | +0.93 | reproduced |
| Kept from the pilot: norm violation | (see pilot) | | +1.73 | reproduced |
| Five null pairs | none expected | | largest 0.47 | 0 of 5 crossed |

- **The bike lanes.**
  - The panel puts Maya's intention near the floor in both versions. On the full OffTheRails data, the persona Claude panel gave +0.15 for this contrast against people's +0.34 (`reports/Fixing the panel's overconfidence.md`).
  - The blind spot is the intention question. On permissibility, the same calibration found the panel does respond to avoidability (−0.39 against people's −0.24).
  - Two authored pairs on this factor did show gaps (Haiku's flood, Opus's bees), with causal and blame questions. Whether people would show them is untested.
- **The bath** matches people's gap almost exactly (+0.80 against +0.83), though the panel sits higher on the scale.
- **Classic controls overall: 4 of 5 reproduced.**

## Test-retest on the reused pairs

15 pairs were judged by two independent persona panels of the same design: the pilot's persona run, and round 2 (new personas, and new pairs mixed into each batch). They are 8 authored pairs on doing vs allowing and norm violation, 2 classic controls and 5 nulls.

- **Effects:** correlation 0.93; mean absolute difference 0.23 points; largest 0.73.
- **2 of 15 verdicts change:**

  | Pair | Pilot persona run | Round 2 | Prediction score |
  |---|---|---|---|
  | Haiku, doing vs allowing | −0.47, none | −1.13, B higher | 0 → 0 (Haiku had predicted A higher) |
  | Fable, norm violation ("Storage shelf") | +0.20, none | +0.93, A higher | **0 → 1.00** |

So between two runs of the same panel, one of 8 authored pairs went from no credit to full credit.

## How fragile the scores are

To estimate a rerun with judges like these, I resampled the ratings inside each judge-model × version cell (300 reruns) and applied the scoring rule each time. This understates real rerun noise, because personas and batch context stay fixed.

- **Robust:**
  - Opus's beehive (0.92) and farm-gate (0.96) pairs.
  - Sonnet's circuit pair (0.86).
  - The zero of Sonnet's greenhouse (0.96).
  - Haiku's flood overshoot (0.88).
- **Close to coin flips:** Sonnet's babysitter (0.54) and Opus's smoke alarm (confirmed in 32% of reruns).
- **Controls too:**

  | Control | Kept in reruns |
  |---|---|
  | Doing vs allowing | 0.53 |
  | Norm violation | 0.59 |
  | The bath | 0.62 |
  | The pencil box | 0.76 |

- **Why:** the gap rule needs all three judge models to agree on the sign, and each model's own gap rests on 5 ratings per version. Where one model's gap is near zero, a rerun often flips it. That is often the Haiku judges near the top of the scale (the bath: 6.6 vs 6.4).
- **Author order across the same reruns:**

  | Order | Share of reruns |
  |---|---|
  | Opus > Sonnet > Haiku | 70% |
  | Opus > Haiku > Sonnet | 18% |
  | Sonnet > Opus > Haiku | 9% |
  | Other orders | 3% |

## All five factors together

| Author | Round-2 pairs | Mean prediction score | Mean composite | Pilot, persona panel (current rule) |
|---|---|---|---|---|
| opus | 5 | 0.60 | 66.2 | 72.6 |
| sonnet | 5 | 0.55 | 60.0 | 65.3 |
| haiku | 5 | 0.24 | 46.9 | 56.1 |
| fable | 2 (reused only) | 1.00 | 82.5 | 74.7 |

Fable's figure covers only its two reused pairs and is not comparable. Everyone else scores lower than in the pilot, because the new factors are harder.

## What this means

1. **Replacing the easy factors worked.** The ceiling is gone, and the new factors spread the authors out.
2. **Noise, not factor difficulty, is now the binding constraint.**
   - With one pair per factor and 5 ratings per model and version, about a third of single-pair scores could flip in a rerun.
   - Before author differences are read in detail, the benchmark needs more pairs per author per factor, or more ratings per cell, or both. Three pairs would cut the noise in an author's factor mean by about 40%; 10 repeats instead of 5 would make each model's own gap less likely to flip.
3. **The all-models-agree rule is the main source of fragility** with only three judge models.
   - Adding judge models, or replacing the sign-agreement rule with an interval that resamples the models themselves, would fix it. `score.py` already computes that interval as a sensitivity.
   - I have not changed the rule. Another post-hoc change should be your call, and ideally made before the next data.
4. **Inevitable harm needs a different reader, or people.** On the intention question, the panel misses an effect people show. Scores on this factor say whether an author predicted the panel, not people.
5. **Fable's round 2 is pending:** authoring, auditing and judging, after 26 November.

## Caveats

- One pair per author per factor, three authors. Author differences are descriptive.
- A model panel, not people. On public data, what the persona panel confirms, people back about half the time (`reports/Fixing the panel's overconfidence.md`).
- The new pairs' confound and originality grades come from three auditors; the reused pairs' come from the pilot's four. Both are model opinions.
- Split-half noise is higher than in the pilot. Random halves differ by 0.89 points at the 95th percentile (pilot: 0.46): 15 ratings per version instead of 20, plus the personas' wider spread.
- The bike-lanes control uses OffTheRails' own text, which is public under an MIT licence, so judges may have seen it. The other two controls are this project's paraphrases.

## Judgment calls

1. **Factors.** I picked inevitable harm, knowledge and causation, and luck and wrongness. Each has public human data close enough to anchor a control, and each is small or disputed in the literature. I kept doing vs allowing and norm violation, the two factors the pilot found hard, and reused their pairs unchanged, so round 2 is a complete five-factor set.
2. **Panel.** I used persona judges, because on public human data they behaved more like people than the plain panel. The design matches the pilot's persona run, so the reused pairs double as a test-retest.
3. **Provenance.** An agent may correct its own answer file after writing it. Any other write, or any read before answering besides its own instructions, makes it unusable. This let in one Sonnet judge, which changed one comprehension answer and no rating.
4. **No scoring change.** Round 2 is scored with the rules as they stood before its data existed.
