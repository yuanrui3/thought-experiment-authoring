# Methods note: Thought-experiment authoring pilot

14 November 2026. **Objective:** test whether a model can write an original, controlled thought experiment and correctly predict how readers will judge it. People are the readers that count. This pilot used a panel of Claude models only, so it tests the pipeline: it is not a result about models, and it does not show that the pairs work on people. A human run is deferred.

## Judgment calls I made

1. **Factors.** Intention vs. accident, doing vs. allowing, knowledge vs. lucky true belief, moral luck, and a fifth of my choosing: whether breaking a rule makes someone more of a *cause*.
2. **Authors.** One fresh-context agent per Claude tier (haiku, sonnet, opus, fable), same brief, one pair per factor: 20 pairs. The brief said the readers would be AI models standing in for ordinary readers, and named only your four famous cases, so spotting other re-skins was the author's job.
3. **Prediction sizes.** Bins on the difference in mean rating: none below 0.5 points, small 0.5 to 1.5, large 1.5 or more. Authors were told the bins.
4. **Comprehension.** Three-option multiple choice with a key per version, so it scores mechanically.
5. **Panel.** The same four tiers, 5 repeats, 2 arms: 40 fresh-context judges at low reasoning effort, each rating one randomly chosen version of all 30 pairs in shuffled order. That is 20 ratings per version.
6. **What counts as a gap.** At least 0.5 points, a 95% bootstrap interval (10,000 resamples inside each model-by-version cell) that excludes zero, and three of four judge models agreeing on the sign.
7. **Score.** Prediction and comprehension come from the judges' behavior. Prediction (since 22 November; see item 11): full credit when the measured gap falls inside the predicted range, falling to nothing at 1.5 points outside it, and nothing at all for a pair that should show a gap (authored pairs, classic controls) unless the gap is confirmed in the predicted direction. Confounds and originality are graded by four blind model auditors, taking the harsher middle grade; they are opinions. Composite: 40% prediction, 25% confounds, 20% originality, 15% comprehension. The weights are arbitrary. All rules were fixed in `score.py` before any judgment existed.
8. **Controls.** Classic pairs matched to the five factors, not the five most famous cases; null pairs of graded size, from one changed word to two reworded sentences.
9. **After the prior-art check** I narrowed the claim, kept direction and size as separate results, and added three pairs with a planted confound to test the auditors.
10. **After seeing the data** I added diagnostics and flags (shared settings, auditor agreement, same-model effects). Until 22 November I changed no scoring rule.
11. **On 22 November I changed the prediction score, after seeing these data and public human data.** The original rule gave half for direction and half for the size bin. Tested against real people (`reports/Authors predicting people.md`), it rewarded predicting "no difference": with mostly small human effects, that guess beat every model. The new rule scores the distance between the measured gap and the predicted range, and requires a pair meant to show a gap to show it. It is a post-hoc change, so the original scores are kept beside the new ones on the results page and in `out/pair_scores.csv`; `python3 score.py --prediction-rule classes` reproduces the original results exactly.

## What the checks showed

- **Collection.** 1,200 judgments, every batch complete; transcripts confirm no judge used a tool.
- **Controls.** 5 of 5 classic pairs reproduced; 0 of 5 null pairs crossed the floor (largest 0.30). One null had an interval that excluded zero, and haiku or sonnet alone would each have put 2 of 5 nulls over the floor.
- **Noise.** Random halves of the same scenario differ by up to 0.46 points (95th percentile).
- **Auditors.** 12 of 12 planted confounds caught, 19 of 20 classics recognised, no false alarm on nulls; but any two of them gave a real pair the same confound grade only about half the time.
- **Authored pairs.** 17 of 20 right on direction, 13 of 20 on direction and size. Under the distance rule, 4 authored pairs score 0 on prediction (one opposite gap, two with no confirmed gap, one 4-point gap predicted as small), and the author order is unchanged: sonnet, fable, opus, haiku.

## Limitations

- **Claude judging Claude.** Model panels are reported to give effects two to three times human size and to find effects in most studies where people showed none (Cui, Li and Zhou). Here, judges also favoured pairs from their own model by 0.44 points.
- **Three factors are too easy.** Every author got the direction right on intention, knowledge and moral luck, so those predictions barely test authoring.
- **Originality misses convergence.** 8 of 20 pairs share a setting with another pair; the audit grades pairs one at a time. I flagged these by hand.
- **Two of four components are model opinion,** with low agreement. A broken pair reached the top four.
- **Comprehension is at ceiling** (99.5%) on a model panel.
- **Repeats are not people.** Two models gave identical ratings across repeats in over half the scenarios, so the interval is too narrow; the floor and the model-agreement rule compensate.
- **Judges were tool-enabled agents in batches of 30,** not bare model calls on single items.
- **Classic controls are paraphrases the panel recognises.** Their references were checked against the papers on 15 November and corrected (`docs/control-references.md`). Three controls have no human data for the exact contrast used here, so for them "reproduced" means the expected direction appeared, not that a measured human gap was matched.
- **Five pairs per author.** Author differences are descriptive.

## Next steps

1. Run the same pairs on people and re-set the size bins on that data. The survey and its analysis plan are ready (`docs/human-survey.md`); the project is paused until participants are found.
2. Add judges from other vendors; `judgments.csv` already carries type, vendor, model and group.
3. Replace easy factors with contested ones, and have authors hit a target size.
4. Score originality across the whole set, so shared settings count against a pair.
5. Add trained human auditors and placebo questions, so confounds are measured by behavior.
6. Anchor classic controls to public human data (OffTheRails, MoCa, replication archives).

## Closest prior work

Nothing found scores an author on its own free-text pair by a blind reader split (see `docs/prior-art.md`). Nearest: OffTheRails (Fränken et al. 2024), Automated Social Science (Manning, Zhu and Horton 2024), the Counterexample Game (Drucker and Mahowald 2026), HumanStudy-Bench (Liu et al. 2026), PhilosophyBench (Stanford 2026), and Cui, Li and Zhou (2024).
