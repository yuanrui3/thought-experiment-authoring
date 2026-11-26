# Methods note: Thought-experiment authoring pilot

14 November 2026. **Objective:** test whether a model can write an original, controlled thought experiment and correctly predict how readers will judge it. People are the readers that count. This pilot used a panel of Claude models only, so it tests the pipeline: it is not a result about models, and it does not show that the pairs work on people. A human run is deferred.

## Judgment calls I made

1. **Factors.** Intention vs. accident, doing vs. allowing, knowledge vs. lucky true belief, moral luck, and a fifth of my choosing: whether breaking a rule makes someone more of a *cause*.
2. **Authors.** One fresh-context agent per Claude tier (haiku, sonnet, opus, fable), same brief, one pair per factor: 20 pairs. The brief said the readers would be AI models standing in for ordinary readers, and named only your four famous cases, so spotting other re-skins was the author's job.
3. **Prediction sizes.** Bins on the difference in mean rating: none below 0.5 points, small 0.5 to 1.5, large 1.5 or more. Authors were told the bins.
4. **Comprehension.** Three-option multiple choice with a key per version, so it scores mechanically.
5. **Panel.** The same four tiers, 5 repeats, 2 arms: 40 fresh-context judges at low reasoning effort, each rating one randomly chosen version of all 30 pairs in shuffled order. That is 20 ratings per version.
6. **What counts as a gap.** At least 0.5 points, a 95% bootstrap interval (10,000 resamples inside each model-by-version cell) that excludes zero, and three of four judge models agreeing on the sign. Since 24 November the agreement needed is two-thirds of the judge models, rounded up (item 14). That is still three of four for the pilot, but two of three for the three-model panels used since.
7. **Score.** Prediction and comprehension come from the judges' behavior. Prediction (since 22 November; see item 11): full credit when the measured gap falls inside the predicted range, falling to nothing at 1.5 points outside it, and nothing at all for a pair that should show a gap (authored pairs, classic controls) unless the gap is confirmed in the predicted direction. Confounds and originality are graded by four blind model auditors, taking the harsher middle grade; they are opinions. Composite: 40% prediction, 25% confounds, 20% originality, 15% comprehension. The weights are arbitrary. All rules were fixed in `score.py` before any judgment existed.
8. **Controls.** Classic pairs matched to the five factors, not the five most famous cases; null pairs of graded size, from one changed word to two reworded sentences.
9. **After the prior-art check** I narrowed the claim, kept direction and size as separate results, and added three pairs with a planted confound to test the auditors.
10. **After seeing the data** I added diagnostics and flags (shared settings, auditor agreement, same-model effects). Until 22 November I changed no scoring rule.
11. **On 22 November I changed the prediction score, after seeing these data and public human data.** The original rule gave half for direction and half for the size bin. Tested against real people (`reports/Authors predicting people.md`), it rewarded predicting "no difference": with mostly small human effects, that guess beat every model. The new rule scores the distance between the measured gap and the predicted range, and requires a pair meant to show a gap to show it. It is a post-hoc change, so the original scores are kept beside the new ones on the results page and in `out/pair_scores.csv`; `python3 score.py --prediction-rule classes` reproduces the original results exactly.
12. **Round 2 (22 November) replaced the three easy factors** with inevitable harm, knowledge and causation, and luck and wrongness, each with a classic control anchored to public human data. Haiku, Sonnet and Opus wrote one pair each (Fable pending its usage limit). A persona panel of the same design as the pilot's persona run judged them, together with the pilot's doing-vs-allowing and norm pairs, reused unchanged. The scoring rules were not changed. Details and the judgment calls behind them: `reports/Round 2 contested factors.md`.
13. **Round 2b (22 November) gave each round-2 author three pairs per new factor.** Each wrote two more pairs per factor, and all 27, with the controls, were judged together by a second persona panel. The round-2 pairs' scores changed a lot between the two runs, so I withdrew round 2's claim that the new factors are harder. A second, independent panel on the same batches then showed that the gaps reproduce within sampling noise. What doesn't reproduce is the verdict near a threshold. Pooling the two panels (10 ratings per model and version) halves the expected flips, and judge-level resampling is now the error bar. Details: `reports/Round 2b three pairs per factor.md` and `reports/Round 2b two panels.md`.
14. **On 24 November I changed the agreement rule, at your request, after seeing the data.** A confirmed gap needed 75% of the judge models to agree on its sign. With three models, that meant all three, and the Haiku judges at the top of the scale vetoed real gaps, including two classic controls. It now needs two-thirds, rounded up: 2 of 3, and 3 of 4 as before. Verdicts are much more stable between panels. But on public human data, the three-model persona panel now confirms twice as many gaps that people don't show (10 → 20). `--agreement-rule three_quarters` reproduces every earlier score. Details: `reports/Agreement rule change.md`. *(Correction, 26 November: Haiku was near the top of the scale for the two classic controls. On authored pairs, the dissenting model was mostly mid-scale; see item 18.)*
15. **On 25 November you adopted a second score, the shared-pool prediction score** (option B). Every author predicts the gap, in points, for every item of a round, after writing and before judging. It is scored on other authors' pairs and the controls, and reported beside the composite, never folded into it. Two authors are compared only on items neither wrote. Its definition was committed before any prediction for the next round was collected. Details: `reports/Shared-pool prediction score.md`.
16. **Round 2c (26 November) put all four authors on one panel.** Fable wrote nine pairs from the same two briefs the others had used. All four authors predicted every item before judging. Then 80 persona judges, 10 per model and version from all four Claude models, judged the 36 authored pairs and 10 controls together.
    - Haiku, Sonnet and Opus audited Fable's pairs, and Fable audited everyone else's. So the other authors' pairs carry four audits (upper median) and Fable's carry three (median). That costs Sonnet 2.8 composite points and changes no order.
    - Composite: Opus 80.7, Sonnet 76.1, Fable 70.7, Haiku 70.0.
    - Shared pool: Fable 72.2 and Opus 69.9 (a tie on items neither wrote), then Sonnet 62.0 and Haiku 57.0.
    - Details: `reports/Round 2c Fable joins.md`.
17. **On 26 November, after seeing round 2c, you gave the shared-pool score equal weight with the composite.** The summary score is 0.5 × composite + 0.5 × shared-pool score, with both parts still reported unchanged beside it.
    - In components, that is 50% shared-pool prediction, 20% own-pair prediction, 12.5% confounds, 10% originality and 7.5% comprehension.
    - Neither part is rescaled to the field, so an author's summary doesn't depend on who else is in the round.
    - It applies from round 2c on; the pilot keeps the composite alone.
    - Round 2c: Opus 75.3, Fable 71.4, Sonnet 69.0, Haiku 63.5. Opus is first in 96.5% of combined judge- and item-level draws, but not clearly ahead of Fable. The order holds for any weighting between 35/65 and 65/35.
    - Details: `reports/Summary score.md`.
18. **On 26 November I tested the "cheaper fix" for the ceiling veto and rejected it.** The fix was to return to the three-quarters rule but let a judge model that rates both versions at the top or bottom of the scale abstain. The criteria were committed before the test ran, and it failed all three:
    - On the persona panel, only 41% of the gaps it confirms on public human data are backed by people (needed 50%; the two-thirds rule gets 39%). On MoCa's yes/no questions the model judges answer almost unanimously, so a model abstained on 72 of 85 pairs.
    - It leaves 5 of 27 round-2b scores changing between panels (needed at most 2), the same as the old rule.
    - A null control is confirmed in round 2b's panel 2 under every rule, so this criterion couldn't separate them. I should have written it relative to the current rule.

    The two-thirds rule stays. The test also corrects item 14: of the ten gaps confirmed with one model dissenting, the dissenter was at or near the top of the scale in five. In the other five it sat mid-scale and saw no gap. Details: `reports/Ceiling abstention test.md`.
19. **On 26 November I tested weighting judge models by how well they track people, and rejected it.** Each model's weight was max(0, its average raw correlation with the human gaps on OffTheRails and MoCa). A gap then needs the models agreeing in sign to carry two-thirds of the weight. The criteria were committed first, and it failed two of three:
    - Out of sample (weights from one dataset scoring the other), 45% of the persona panel's confirmed gaps are backed by people. That's better than two-thirds (39%) but short of the 50% bar. It does confirm the most real human gaps: 14.
    - Stability is as poor as the old rule: 6 of 27 round-2b scores change between panels, and 5.7 are expected in a rerun.
    - The reason is that Haiku, the usual dissenter, tracks people as well as the others, so it gets 40% of the weight and its veto returns.
    - In sample the rule looks better (57%), but that's the weights fitting their own data.

    Three replacement rules have now been tested. None gives both stable verdicts and verdicts people back, so the two-thirds rule stays. Details: `reports/Judge weighting test.md`.
20. **On 26 November I tested more ratings per judge model.** A second, independent 80-judge panel rejudged round 2c, giving 20 ratings per model and version pooled. Fable's 10 persona judges also ran on the public human data, completing the four-model persona calibration.
    - By the criteria committed first, 20 ratings don't become the standard: expected score changes per rerun fall only from 1.0 to 0.7 of 36 pairs (needed: half).
    - But the real rerun moved more than that estimate:
      - 3 of 36 authored scores changed.
      - Two of Sonnet's pairs fell just under the 0.5 bar.
      - The null control "weekday" was confirmed in panel 2. Pooling fixed it.
    - More judges cost no validity on human data.
    - The four-model persona panel round 2c uses is backed by people on 42% of the gaps it confirms.
    - Round 2c's headline is now the pooled panel: summary Opus 77.0, Fable 73.6, Sonnet 70.0, Haiku 63.8.
    - One deviation from the committed analysis: the 5-judge calibration halves were redrawn until every story was covered. Details: `reports/More ratings per judge model.md`.

## What the checks showed

- **Collection.** 1,200 judgments, every batch complete; transcripts confirm no judge used a tool.
- **Controls.** 5 of 5 classic pairs reproduced; 0 of 5 null pairs crossed the floor (largest 0.30). One null had an interval that excluded zero, and haiku or sonnet alone would each have put 2 of 5 nulls over the floor.
- **Noise.** Random halves of the same scenario differ by up to 0.46 points (95th percentile).
- **Auditors.** 12 of 12 planted confounds caught, 19 of 20 classics recognised, no false alarm on nulls; but any two of them gave a real pair the same confound grade only about half the time.
- **Authored pairs.** 17 of 20 right on direction, 13 of 20 on direction and size. Under the distance rule, 4 authored pairs score 0 on prediction (one opposite gap, two with no confirmed gap, one 4-point gap predicted as small), and the author order is unchanged: sonnet, fable, opus, haiku.

## Limitations

- **Claude judging Claude.** Model panels are reported to give effects two to three times human size and to find effects in most studies where people showed none (Cui, Li and Zhou). Here, judges also favoured pairs from their own model by 0.44 points.
- **Three factors are too easy.** Every author got the direction right on intention, knowledge and moral luck, so those predictions barely test authoring. Round 2 replaced them, but whether the new factors are harder is unsettled. One panel run scored the same three authors 0.44 on them, and a second run scored the same pairs 0.73 (round 2b). One new control (avoidable harm and intention) fails in both runs, on a known blind spot of the panel.
- **Originality misses convergence.** 8 of 20 pairs share a setting with another pair; the audit grades pairs one at a time. I flagged these by hand.
- **Two of four components are model opinion,** with low agreement. A broken pair reached the top four.
- **Comprehension is at ceiling** (99.5%) on a model panel.
- **Repeats are not people.** Two models gave identical ratings across repeats in over half the scenarios, so the interval is too narrow; the floor and the model-agreement rule compensate.
- **Judges were tool-enabled agents in batches of 30,** not bare model calls on single items.
- **Classic controls are paraphrases the panel recognises.** Their references were checked against the papers on 15 November and corrected (`docs/control-references.md`). Three controls have no human data for the exact contrast used here, so for them "reproduced" means the expected direction appeared, not that a measured human gap was matched.
- **Five pairs per author.** Author differences are descriptive.
- **Verdicts near a threshold are noisy.** With 5 ratings per model and version, independent panels give gaps that agree within sampling noise. But 5 of 27 authored pairs still change score, because a gap crosses 0.5 or one model's sign flips. The all-models-agree rule also lets one judge model at the scale's ceiling veto real gaps; it blocks two classic controls in both panels. Pooling two panels halves the flips.

## Next steps

1. Run the same pairs on people and re-set the size bins on that data. The survey and its analysis plan are ready (`docs/human-survey.md`); the project is paused until participants are found.
2. Add judges from other vendors; `judgments.csv` already carries type, vendor, model and group.
3. Replace easy factors with contested ones (done in round 2), and have authors hit a target size (not yet). Round 2b added pairs per author and a second panel. The agreement rule was settled on 24 November (item 14). A points target was then tested on the round-2b pairs (`reports/Point predictions.md`): on their own nine pairs Sonnet and Opus did not separate, but on all 37 shared items Opus was clearly the best predictor. That suggests scoring prediction on a shared pool, next to the authoring score. This was adopted on 25 November (item 15) and first used in round 2c (item 16), where the two scores ranked authors differently: Opus and Sonnet lead on the composite, while Fable and Opus lead on the shared pool. The own-pair prediction score also has a weakness. When every author misjudges a factor's size the same way, as all four did on knowledge and causation, it ranks them by how strong their manipulation happened to be. Since 26 November the two scores carry equal weight in a summary score (item 17).
4. Score originality across the whole set, so shared settings count against a pair.
5. Add trained human auditors and placebo questions, so confounds are measured by behavior.
6. Anchor classic controls to public human data (OffTheRails, MoCa, replication archives).

## Closest prior work

Nothing found scores an author on its own free-text pair by a blind reader split (see `docs/prior-art.md`). Nearest: OffTheRails (Fränken et al. 2024), Automated Social Science (Manning, Zhu and Horton 2024), the Counterexample Game (Drucker and Mahowald 2026), HumanStudy-Bench (Liu et al. 2026), PhilosophyBench (Stanford 2026), and Cui, Li and Zhou (2024).
