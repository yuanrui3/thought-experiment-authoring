# Calibration of the model panel on public human data

*22 November 2026. All numbers come from `reports/calibration_numbers.json`, which `pipeline/calibration/analyse.py` rebuilds.*

## Bottom line

**The Claude panel is not a stand-in for people on these judgments, and its errors are systematic, not noise.** Two public datasets have human ratings of near-identical story pairs. I ran the same four-model panel as the pilot on them and applied the pilot's own confirmed-gap rule:

- **Precision.** Of the 24 gaps the panel confirmed, humans backed **8 (33%)**. One had the opposite sign.
- **False alarms.** Where humans showed no reliable gap, the panel confirmed one in **15 of 40 cases (38%)**.
- **Coverage.** It found **8 of the 20** gaps humans did show.
- **MoCa.** On the second dataset, the correlation between panel gaps and human gaps is only **0.23**.

The errors depend on the factor, and they run in both directions:

- **The panel exaggerates textbook distinctions.** Means vs side effect moves panel permissibility ratings by −0.68 scale points; humans move −0.07. The panel's effect is ten times larger.
- **The panel under-reacts to things people respond to.** Norm violations change people's causal judgments about twice as much as the panel's. Whether the agent knew changes people's judgments (0.29) and barely moves the panel (0.03).

Because the bias is systematic, more repeats will not fix it, and tightening the rule doesn't either:

- Doubling the threshold leaves 8 false positives against 7 backed gaps.
- The panel's ratings are 2–7 times less spread than people's, so its intervals are far too narrow. "Interval excludes zero" is almost automatic.

**For the benchmark:**

- Panel verdicts measure agreement with Claude, not with people.
- Scoring the authored pairs needs the human data.
- The panel can still serve as a pre-screen, and later as a prior worth roughly 20–25 participants per pair. That prior has a large caveat; see "What this means for the benchmark".

## Judgment calls

1. **Datasets.**
   - OffTheRails Experiment 2 (Fränken et al. 2024; [cicl-stanford/moral-evals](https://github.com/cicl-stanford/moral-evals), MIT licence).
   - MoCa (Nie et al. 2023; [cicl-stanford/moca](https://github.com/cicl-stanford/moca)).

   Both are public and free. Both have per-story human data on small manipulations of the same story. Story texts are not copied into this repository; MoCa has no licence file. Only ids and numbers are stored.
2. **Panel.** The pilot's four models (haiku, sonnet, opus, fable), 10 judges each.
   - Each judge read one file: 10 OffTheRails stories, one per scenario, in rotating conditions, and 25 MoCa stories, one per group of look-alikes.
   - So, as in the pilot, no judge saw two versions of the same story.
3. **Scale.** OffTheRails uses 1–5, not 1–7. The pilot's 0.5-point threshold is rescaled by range to **0.33**.
4. **Unit of comparison (OffTheRails).** One scenario × one factor × one question, pooled over the other two factors: 10 × 3 × 2 = 60 contrasts.
   - Each side has about 92 human ratings and about 20 panel ratings.
   - The panel gap is the mean of the four models' gaps, as in `score.py`.
   - The panel interval is `score.py`'s stratified bootstrap.
5. **Human verdict.** A contrast counts as a human gap when its 95% interval excludes zero. The interval resamples workers, because each worker gave 16 ratings.
   - A "human null" means no gap was detected with about 92 ratings per side. It does not mean the gap is zero.
6. **MoCa pairs.** Stories with the same question and at least 85% word overlap.
   - A human gap counts as clear at a yes-share difference of at least 0.30.
   - It counts as significant by a two-proportion test (25 votes per story).
   - The panel's "confirmed" bar for MoCa (0.25) is my choice; the pilot has no analogue.
7. **OffTheRails coding.** The public long-format file codes conditions as 0/1. I recovered the coding by matching each worker's 16 rows to the stimulus file for their batch:
   - causal structure: 1 = harm as a means, 0 = side effect;
   - evitability: 1 = evitable, 0 = inevitable;
   - action: 1 = the agent acts, 0 = the agent does not prevent a colleague's act.

   110 of 115 workers match exactly. Dropping the other 5 changes nothing (see "Sensitivity").
8. **b09 kept.** That judge made one extra tool call after writing its answers: a failed attempt to archive a session. The call could not have shown it anything.

## What was run

| | OffTheRails (Exp. 2) | MoCa |
|---|---|---|
| Stories | 10 scenarios × 8 conditions (2 × 2 × 2) | 85 near-minimal pairs (89 stories; 78 causal pairs, 7 moral) |
| Question | "What X did is morally permissible" and "X intended the negative outcome", 1–5 agree | The dataset's yes/no question |
| Humans | 115 workers × 16 ratings = 1,840 | 25 votes per story |
| Panel | 400 ratings (each item 4–7 times) | 1,000 answers (each story 4–20 times) |

**Provenance.** `pipeline/calibration/check_judges.py` reads every judge transcript.

- All 40 judges were served the model requested: claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5 and claude-fable-5-2.
- 39 made exactly two tool calls: Read of their own batch, then Write of their own answers.
- b09 is the exception described in judgment call 8.
- All 40 answer files are complete and well-formed.
- The four recognition agents read only the recognition file and wrote only their answers.
- The haiku recognition agent also created a placeholder task suggestion and withdrew it at once.

## OffTheRails results

### Main effects

Gap in mean rating, in scale points on 1–5, averaged over the 10 scenarios. A positive number means the first-named level was rated higher. Intervals are 95%, resampling workers or judges.

| Contrast | Question | Humans | Panel | haiku | sonnet | opus | fable |
|---|---|---|---|---|---|---|---|
| means − side effect | permissible | −0.07 [−0.15, +0.01] | **−0.68** [−0.77, −0.57] | −0.72 | −0.73 | −0.75 | −0.50 |
| means − side effect | intended | +0.20 [+0.09, +0.31] | **+0.79** [+0.67, +0.92] | +0.55 | +0.63 | +1.11 | +0.89 |
| evitable − inevitable | permissible | −0.24 [−0.34, −0.14] | −0.39 [−0.52, −0.26] | −0.44 | −0.29 | −0.40 | −0.44 |
| evitable − inevitable | intended | **+0.34** [+0.21, +0.46] | +0.08 [−0.06, +0.21] | +0.10 | +0.29 | −0.12 | +0.06 |
| acts − does not prevent | permissible | **+0.11** [+0.04, +0.19] | **−0.09** [−0.20, +0.02] | −0.20 | +0.06 | −0.16 | −0.06 |
| acts − does not prevent | intended | +0.04 [−0.05, +0.12] | +0.21 [+0.11, +0.33] | +0.42 | +0.18 | +0.28 | −0.02 |

- **Means vs side effect.** All four models apply the textbook doctrine of double effect hard. People barely do.
- **Evitability.** People think an agent who could have avoided the harm intended it more (+0.34). The panel does not (+0.08).
- **Acting vs not preventing.** On permissibility, people and panel lean in opposite directions, though both effects are small.

### Verdicts on the 60 scenario-level contrasts

| Panel verdict (pilot rule) vs human data | Count |
|---|---|
| Confirmed, and humans show the same gap (hit) | 8 |
| Confirmed, humans show no reliable gap (false positive) | 15 |
| Confirmed, humans show the opposite gap (sign error) | 1 |
| Not confirmed, humans show a gap at or above the threshold (miss) | 6 |
| Not confirmed, humans show a smaller gap (miss) | 5 |
| Not confirmed, humans show none (correct null) | 25 |

- **Where the false positives sit.** 12 of the 15 are means vs side effect.
  - In the false positives, the panel's gap averages 0.70 and the human gap 0.10.
  - Humans lean the same way in 10 of the 15. So the panel is mostly exaggerating tiny real effects about sevenfold, not inventing them from nothing.
- **Misses.** These are mostly evitability on the intention question: 6 of 10 scenarios.
- **Acting vs not preventing.** 19 of 20 contrasts are correct nulls. The panel did not invent doing/allowing gaps where people had none.

### Agreement in size and direction

| | Raw r | r corrected for reliability | Panel ÷ human mean \|gap\| | Same sign where humans show a gap |
|---|---|---|---|---|
| All 60 | 0.51 | 0.68 | 1.9× | 18 of 20 |
| Permissibility (30) | 0.42 | 0.57 | 2.2× | 10 of 11 |
| Intention (30) | −0.09 | −0.17 | 1.7× | 8 of 9 |

- **Reliability.** Split halves, Spearman–Brown corrected:
  - humans 0.67 (permissibility 0.71, intention 0.36);
  - panel 0.87 (0.76, 0.70).

  The corrected correlation is therefore not held down by noise. On intention, the panel's ordering of contrasts is unrelated to people's.
- **Per model.**
  - r with humans: haiku 0.39, sonnet 0.50, opus 0.39, fable 0.57.
  - Same sign where humans show a gap: 65%, 80%, 65%, 65%.
  - Opposite sign: 15%, 5%, 30%, 5%.

  No single model is good enough alone. The averaged panel does better on direction (90%) than any single model.
- **Levels and spread.** Mean permissibility: humans 4.07, panel 3.92. Mean intention: humans 2.20, panel 1.48. The typical spread of ratings for one version of a story (within-condition SD) is:

  | Question | People | Panel | Within one model |
  |---|---|---|---|
  | Permissibility | 0.79 | 0.44 | 0.14 |
  | Intention | 1.03 | 0.30 | 0.15 |

  This is why the panel's intervals are so narrow. Resampling repeats of one model measures that model's sampling noise, not how much people differ.

### Could a different rule fix it?

Each variant is scored against the same human verdicts. These rules were picked after seeing these 60 contrasts, so any of them would need checking on fresh data.

| Rule | Confirmed | Backed by humans | False positives | Sign errors |
|---|---|---|---|---|
| Pilot rule (0.5 on 1–7) | 24 | 8 | 15 | 1 |
| Threshold 1.0 on 1–7 | 15 | 7 | 8 | 0 |
| Threshold 1.5 on 1–7 | 3 | 1 | 2 | 0 |
| Interval with human-sized spread (SD 0.97) | 19 | 8 | 11 | 0 |
| All four models must agree | 20 | 8 | 11 | 1 |

- No variant gets precision much above 50% without losing nearly every true gap.
- The problem is bias concentrated in one factor, and the four models share it, so neither agreement nor width helps.

### Sensitivity

- **First exposure only.** The human participants saw 16 stories, some scenarios twice in different conditions. The panel saw each scenario once.
  - Keeping only each person's first exposure to each scenario (1,129 ratings): human gaps correlate 0.91 with the full data, and 0.47 with the panel (0.51 with all data).
  - This assumes the file's row order is presentation order. The experiment code saves trials in the order shown, but I have not confirmed the file keeps it.
- **Dropping the 5 workers whose rows don't match their batch file:** human gaps correlate 0.99 with the full data, and 0.56 with the panel.

## MoCa results

| | Value |
|---|---|
| Correlation, panel gap vs human gap (85 pairs) | 0.23 (0.28 corrected; reliability: humans 0.86, panel 0.81) |
| Panel ÷ human mean \|gap\| | 0.71× (panel under-reacts) |
| Where the human gap is ≥ 0.30 (34 pairs) | same sign 44%, no panel gap 35%, opposite 21% |
| Verdicts | hit 4, false positive 10, sign error 0, miss 37, correct null 34 |
| False positives among human nulls | 10 of 44 (23%) |
| Story level: majority answer matches humans | 62% (panel says yes 63% of the time, humans 50%) |
| Per model r | haiku 0.16, sonnet −0.03, opus 0.26, fable 0.30 |

The panel often gives the same answer to both stories of a pair where people split. MoCa's own sentence annotations show which factor differs within each pair:

| Factor that differs | Pairs | Human gap clear | Panel same / zero / opposite | Mean \|gap\| humans vs panel | r |
|---|---|---|---|---|---|
| Event normality (norm violation) | 30 | 19 | 10 / 6 / 3 | 0.36 vs 0.17 | 0.41 |
| Causal structure | 16 | 8 | 6 / 1 / 1 | 0.29 vs 0.28 | 0.45 |
| Agent awareness | 12 | 6 | 1 / 4 / 1 | 0.29 vs **0.03** | −0.14 |
| Timing | 9 | 3 | 1 / 2 / 0 | 0.24 vs 0.20 | 0.09 |
| No annotated difference | 29 | 5 | 1 / 2 / 2 | 0.17 vs 0.18 | −0.05 |

The "no annotated difference" pairs work as a rough null set. There the panel confirms 5 gaps that humans don't show, and humans show 7 that the panel misses.

## Did the models know these stories?

Each model read all 99 calibration stories in one file. For each it was asked whether it recognised the story and where it comes from.

| | OffTheRails (10) | MoCa (89) |
|---|---|---|
| haiku | 10 "yes", all attributed to Knobe (2003). That is the wrong source; the stories are generated from a 2024 template. | 8 "yes" |
| sonnet | 0 "yes" | 89 "yes": 22 name authors (2 with a year); the other 67 restate the story with a genre label, such as "Bash Ball omission/norm causation vignette" |
| opus | 10 "yes", all naming OffTheRails (Fränken et al. 2024) | 89 "yes", every one naming a dataset or a dated paper; 45 name MoCa or BIG-Bench causal_judgment |
| fable | 10 "yes", all naming OffTheRails | 89 "yes", every one naming a dataset or a dated paper; 34 name MoCa or BIG-Bench |

- **Opus and Fable know both datasets by name.** So recognition can't be compared within those models: they recognised everything.
- **The haiku and sonnet answers don't vary where it matters.** There are no pairs with a clear human gap that one of these models recognised and another didn't. So recognition can't be tested there either.
- **What this implies.** Contamination can only push agreement *up*, yet agreement is weak. And Opus and Fable are not clearly better than the two models that didn't know the sources (OffTheRails r 0.39 and 0.57 against 0.39 and 0.50). These numbers are, if anything, optimistic for newly written vignettes.

## What this means for the benchmark

**Per factor:**

1. **Intention vs accident.** The nearest analogue is means vs side effect, and on it the panel strongly amplifies the textbook distinction. Expect the panel to reward "large" predictions that people would rate small.
2. **Doing vs allowing.** The analogue is acting vs not preventing a colleague's act. It is not a clean analogue: who acts also changes.
   - The panel did not invent gaps; 19 of 20 contrasts were correct nulls.
   - But on the overall permissibility effect it leans the textbook way while people lean slightly the other way.
   - Small doing/allowing effects from the panel should not be trusted for direction.
3. **Rule-breaking makes someone more of a cause (the fifth factor).** The analogue is MoCa's event-normality pairs.
   - The panel usually gets the direction (10 right, 3 wrong, 6 no gap) but at half the human size.
   - It fails to confirm 19 of the 21 pairs where humans show a significant gap.
   - Expect the panel to score "none" predictions as right when people would show an effect.
4. **Knowledge vs lucky true belief.** The only analogue is MoCa's agent awareness, a different construct: awareness affecting causal and moral judgments. The panel is nearly blind to it there. Treat this as a warning, not a measurement.
5. **Moral luck.** These data have no analogue.

**For the scoring pipeline:**

- **Read the pilot's results as agreement with Claude.**
  - Of panel-confirmed gaps, about a third would hold for people.
  - About 4 in 10 human nulls get confirmed.
  - The prediction split and size scores in `results.html` measure whether authors predicted Claude, which the methods note already says. This report puts a number on how far that is from people.
- **Keep the panel for what it can do.**
  - Pre-screening: comprehension failures, confounds, unreadable pairs.
  - Later, a prior.
- **The prior.** On OffTheRails, true human gaps scatter around the panel's by τ ≈ 0.6 on the 1–7 scale (0.4–0.5 within one question).
  - With the math note's formula 4σ²/τ², that prior is worth about 17–29 participants per pair, depending on which human spread is used for σ (1.2–1.5 on 1–7); call it 20–25.
  - But τ is about twice the typical human gap here (≈0.3 on 1–7). The prior can tell large effects from none, not small effects from none.
  - The bias is also factor-specific, so a single calibration slope won't remove it. Calibrate per factor once the survey data exist.
- **Two rules for any panel-only verdict.**
  1. Build intervals with a human-sized spread, not the panel's. This cut false positives from 15 to 11 here.
  2. Label the verdict "Claude panel".
- **Restrict the judges' tools.** One judge tried to archive a session, and one recognition agent created and withdrew a task suggestion. General-purpose agents can reach session and task tools. Future runs should use a judge agent type limited to Read and Write.

## Reproduce

The run used moral-evals at commit `e8e063a5979eeafa867018c29eba988e2297072b` and moca at commit `1b61a20294247480d64675ceb19751ef4e1e878f`.

```bash
git clone https://github.com/cicl-stanford/moral-evals ext/moral-evals && git -C ext/moral-evals checkout e8e063a5979eeafa867018c29eba988e2297072b
```

```bash
git clone https://github.com/cicl-stanford/moca ext/moca && git -C ext/moca checkout 1b61a20294247480d64675ceb19751ef4e1e878f
```

```bash
python3 pipeline/calibration/build_batches.py --moral-evals ext/moral-evals --moca ext/moca --out jb
```

```bash
python3 pipeline/calibration/build_recognition.py --moral-evals ext/moral-evals --moca ext/moca --out jr/stories.txt --key pipeline/calibration/recognition/key.json
```

The judge prompt was the same for every batch: read only `jb/bNN.txt`, answer as an ordinary reader, write `bNN.json`. The answers are in `pipeline/calibration/answers/` and `pipeline/calibration/recognition/`. To check provenance from the transcripts and rerun the analysis:

```bash
python3 pipeline/calibration/check_judges.py --transcripts <subagent transcript dir> --answers pipeline/calibration/answers --out pipeline/calibration/provenance.json
```

```bash
python3 pipeline/calibration/analyse.py --answers pipeline/calibration/answers --moral-evals ext/moral-evals --moca ext/moca --recognition pipeline/calibration/recognition --recognition-key pipeline/calibration/recognition/key.json --provenance pipeline/calibration/provenance.json --out reports/calibration_numbers.json --boot 4000 --splits 400
```

Both build scripts reproduce, byte for byte, the files the judges read. The analysis is seeded: rerunning it gives the same numbers.
