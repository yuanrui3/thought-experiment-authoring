# Mathematical analysis of the benchmark

18 November 2026. Computed from the pilot data by `pipeline/math_analysis.py`; numbers in `reports/math_analysis_numbers.json`. Where human data are needed I assume a rating SD of 1.5 on the 1–7 scale, at the optimistic end of what Kneer & Machery report for similar vignettes (SDs 1.5–2.0). With SD 2.0, every sample size below grows by about 1.8×.

## Summary

1. **On the model panel, the authors' predictions add nothing over knowing the factor.** Guessing "whatever the other authors' pairs on this factor did" scores 0.82, exactly the authors' own mean. Guessing "textbook direction, always large" scores 0.78. The factor alone explains 83% of the variance in gaps.
2. **Two factors carry no information at all.** All four intention pairs and all four knowledge pairs landed in the same verdict (large, predicted direction), so every author scored the same on them. That is the participant's "easy", measured.
3. **The prediction score is not strictly proper.** Its partial credit for adjacent sizes pulls the best report towards "small": an author should report a size other than the one they think most likely in about one case in five.
4. **The size bins cannot be resolved with a feasible human sample.** With 8 people per version, a gap must exceed 1.47 points before its interval excludes zero, so the "small" bin is unreachable. Confirming a true 1.0-point gap half the time takes about 18 people per version; a 0.5-point gap, about 70.
5. **The calibration bar I proposed would fail for the wrong reasons.** Even if people's gaps exactly matched the panel's, "same verdict on 24 of 30 pairs" would be met only 9% of the time with 20 people per version. If people's gaps are half the panel's, as published work suggests, it is unattainable at any sample size here. The null-control part has a 23% chance of failing by luck alone. I am withdrawing it; a replacement is below.
6. **Looking at the results as people arrive inflates false gaps from 6% to 24%** on a null pair, if the classification rule is applied at each look.
7. **The same-model effect is real: +0.44 points** (95% interval +0.10 to +0.82) after controlling for each pair and each judge model. Dropping the author's own model from its pairs' panel changes no verdict in the pilot, so it can be the default at no cost.
8. **The pilot cannot rank its authors.** Shuffling authors within factors gives author differences as large as the observed ones 38% of the time for the prediction score. Detecting a 0.2 difference in mean prediction score needs about 26 pairs per author; 0.1 needs about 100.
9. **The survey is between-subjects per pair, but within-subjects per factor.** Every participant meets both sides of the intention, doing-allowing and knowledge factors, and half of the forms show the two near-identical freezer stories on opposite sides. Judgments under that exposure can differ from single-vignette judgments.
10. **Once human data exist, the model panel can stretch them, but not pair by pair in the way I first wrote.** For an aggregate over pairs (such as an author's mean score), with people rating a random subset of pairs, a panel–human correlation of 0.8 across pairs makes each human-rated pair worth about 2.8; at 0.9, about 5.3. For a single pair, the calibrated panel can act as a prior worth about 4σ²/τ² extra participants, where τ is how far true human gaps scatter around the calibrated panel: 36 at τ = 0.5, 9 at τ = 1.

## 1. What makes a factor informative

Write the gap for pair *p* of factor *f* as Δ_p = μ_f + η_p: a factor-level typical effect plus a pair-specific deviation. An author who knows only the textbook knows μ_f. The part of the outcome that tests the author's own design is η_p.

| Factor | Gaps in the predicted direction | SD | Verdict categories among 4 authors | Entropy (bits) | Prediction scores |
|---|---|---|---|---|---|
| Intention vs. accident | 4.40, 3.50, 3.55, 3.15 | 0.53 | 1 | 0.00 | 1, 1, 1, 1 |
| Doing vs. allowing | −0.80, 0.75, 0.20, 0.70 | 0.72 | 3 | 1.50 | 0, 1, 0.25, 1 |
| Knowledge vs. luck | 4.05, 2.30, 3.45, 2.70 | 0.78 | 1 | 0.00 | 0.75, 1, 1, 1 |
| Moral luck | 0.95, 0.85, 1.85, 1.50 | 0.47 | 2 | 0.81 | 0.75, 1, 1, 0.75 |
| Norm and causation | 1.90, 1.20, 1.85, 0.35 | 0.72 | 3 | 1.50 | 0.75, 1, 1, 0.25 |

- **The factor explains 83% of the variance in gaps.** Most of the outcome is μ_f, which every competent author knows.
- **Entropy of the verdict is the right informativeness index for a binned score.** A factor whose verdict entropy is zero gives every author the same score, whatever they understood. Intention and knowledge are such factors here. (The one 0.75 under knowledge is haiku predicting "small" for a large gap, which is not a design difference.)
- **The baselines make the point sharply.** A predictor using only the other authors' outcomes on the same factor scores 0.82, as the authors do. So on this panel the benchmark measures knowledge of the textbook effect, not design skill.
- **A fix from forecasting:** report a skill score, the author's score minus a factor-level baseline's. On the pilot, that is about zero for every author.

**Why the easy factors are easy, and why the scale makes it worse.** The higher version averages 6.39 of 7 in the intention and knowledge pairs (range 5.80 to 6.95). Under an ordered-probit reading of the scale (latent SD 1.5), a one-point latent shift shows up as a 0.94-point gap mid-scale but only 0.63 at a latent level of 6 and 0.50 at 6.5. So "large" on these factors is mostly the low version falling, and the size partly reflects where on the scale the pair sits, not only how strong the manipulation is.

**What "works" could mean, as a quantity.** A thought experiment earns its keep when its outcome is not foregone and it separates two views. Formally: if theories T₁ and T₂ predict gaps δ₁ and δ₂ for a pair, the pair's discriminating power is roughly |δ₁ − δ₂| / SE, the expected information it gives about which theory readers follow. The intention pairs score near zero on this: every theory predicts a large gap. Two task designs follow:
- **Target-size task:** ask for a pair with a gap of 1.0 ± 0.25 and score the distance. This rewards controlling the manipulation's strength, which a textbook cannot give you.
- **Adjudication task:** name two theories that disagree (for example, blame tracks outcome versus blame tracks foresight), ask for a pair on which they predict different gaps, and score whether the panel's result lands where the author said each theory would put it.

## 2. The prediction score is not strictly proper

The score's matrix (rows: the author's report; columns: the observed verdict):

| Report \ Observed | B large | B small | none | A small | A large |
|---|---|---|---|---|---|
| B large | 1.00 | 0.75 | 0 | 0 | 0 |
| B small | 0.75 | 1.00 | 0.25 | 0 | 0 |
| none | 0 | 0.25 | 1.00 | 0.25 | 0 |
| A small | 0 | 0 | 0.25 | 1.00 | 0.75 |
| A large | 0 | 0 | 0 | 0.75 | 1.00 |

- **The best report is not always the most likely outcome.** Comparing the two A-side reports: E[A small] − E[A large] = 0.25 · (P(A small) + P(none) − P(A large)). So "small" is the better report whenever P(A small) + P(none) > P(A large), even when "large" is the single most likely outcome. Example: beliefs of none 0.25, A small 0.30, A large 0.45 give 0.70 for reporting "small" and 0.675 for "large".
- **Across random beliefs**, the best report equals the most likely outcome in 81% of cases and the median outcome in 65%. The rule elicits neither cleanly; it pulls towards the middle.
- **Bins also interact badly with noisy outcomes.** Scored against a noisy estimate Δ̂, a binned score's expectation depends on how close the true gap sits to a bin edge. A squared-error score does not have this problem: E[(f − Δ̂)²] = (f − Δ)² + SE², so noise adds the same constant for every forecast and the ranking of authors is preserved in expectation.
- **Recommended instead:** ask for a point forecast of the gap plus an 80% interval, and score with squared error (or absolute error) and the interval score. Both are proper. Report them as skill scores against the factor baseline.

## 3. How much a human verdict on one pair can be trusted

The pre-set rule calls a gap confirmed when |Δ̂| ≥ 0.5 and its 95% interval excludes zero, so a gap needs |Δ̂| > 1.96 · SE, where SE = 1.5 · √(2/n) for n people per version.

| People per version | SE of a gap | Smallest gap that can be confirmed | "Small" bin |
|---|---|---|---|
| 8 | 0.75 | 1.47 | unreachable |
| 20 | 0.47 | 0.93 | above 0.93 only |
| 40 | 0.34 | 0.66 | above 0.66 only |
| 80 | 0.24 | 0.50 | whole bin |

Probability that a pair lands in its true category, and the expected score of an author who knows the true gap exactly:

| True gap | n = 8 | n = 20 | n = 40 | n = 80 |
|---|---|---|---|---|
| 0 | 0.50 / 0.61 | 0.71 / 0.78 | 0.86 / 0.90 | 0.96 / 0.97 |
| 0.75 | 0.01 / 0.44 | 0.30 / 0.59 | 0.60 / 0.74 | 0.85 / 0.89 |
| 1.0 | 0.01 / 0.50 | 0.41 / 0.71 | 0.78 / 0.89 | 0.96 / 0.98 |
| 2.0 | 0.75 / 0.87 | 0.85 / 0.96 | 0.93 / 0.98 | 0.98 / 1.00 |

- **A perfect author would score 0.5 on a true 1-point gap with 8 people per version.** Most of what the human run could show about sizes at that scale is noise.
- **The minimum in the survey plan (16 complete responses, so 8 per version) is fit only for large effects.** About 40 per version is needed before small effects mean much, and 70 per version (140 people) before a 0.5-point gap is confirmed half the time.
- **A participant random effect helps only a little.** If 20% of rating variance is a person's general leniency, a mixed model cuts the SE by about 11%.
- **The classic moral-luck control will probably "fail" in people even if the effect is real.** With Kneer & Machery's blame effect (d ≈ 0.33 to 0.39, about 0.5 to 0.6 points), it is confirmed in the expected direction with probability 0.18 to 0.23 at 20 per version and 0.31 to 0.41 at 40.

## 4. A better bar for trusting the model panel

The bar I proposed ("same verdict on at least 24 of 30 pairs, and no null control showing a gap in people that the panel missed") mostly measures human sampling noise:

| If people's true gaps are… | n per version | Expected same verdicts (of 30) | P(at least 24) |
|---|---|---|---|
| equal to the panel's | 20 | 20.7 | 0.09 |
| equal to the panel's | 40 | 24.5 | 0.72 |
| half the panel's | 40 | 15.3 | 0.00 |
| half the panel's | 80 | 17.4 | 0.00 |

And with 5 null controls, the chance that at least one shows a confirmed gap in people by luck is 0.23 at 8 to 40 per version.

**Replacement, to fix before human data arrive:**
- Regress human gaps on panel gaps across the 30 pairs: Δ_human = a + b · Δ_panel + error. Trust the panel for **direction** if the slope b is clearly positive and the correlation corrected for human sampling noise is at least 0.8. With 20 per version, the slope's SE is about 0.06 to 0.07.
- Use b to **rescale** panel gaps to the human scale before binning, instead of expecting the bins to agree.
- Report the residual SD (pair-level disagreement) as the panel's error per pair.
- For nulls, use an equivalence test (interval inside ±0.5) instead of "no confirmed gap".

## 5. Watching results arrive

With seven looks (4, 8, 12, 16, 20, 30 and 40 people per version) and the classification rule applied at each, a null pair shows a false confirmed gap at some point 24% of the time, against 6% for a single look at 40.

So: watch completion counts and comprehension freely, but classify pairs only at one pre-set sample size. If that is impractical, use anytime-valid confidence sequences, which allow continuous monitoring at the price of wider intervals.

## 6. The same-model effect

A two-way model of each judge model's gap on each authored pair (pair effects, judge-model effects, plus an indicator for "judge is the author's own model") gives **+0.44 points** (bootstrap 95% interval +0.10 to +0.82). It inflates the author's own pairs and would inflate their score with any continuous scoring.

Recomputing every authored pair's verdict without the author's own model changes none of the 20 verdicts. Leave-own-model-out should be the default for authored pairs: it removes the bias and, here, costs nothing.

## 7. How many pairs it takes to rank authors

- **Permutation test**, shuffling authors within each factor: p = 0.38 for the prediction score and p = 0.07 for the composite. The composite's apparent spread comes mostly from the audit grades, the least reliable components.
- **Within-factor SD of prediction scores is 0.25.** With 80% power, a 0.2 difference in mean prediction score needs about 26 pairs per author; a 0.1 difference, about 100.

So the next round should have many more pairs per author on fewer, informative factors, not more authors.

## 8. What each survey participant sees

| Factor | Forms (of 20) showing both the high and the low side |
|---|---|
| Intention vs. accident | 20 |
| Doing vs. allowing | 20 |
| Knowledge vs. luck | 20 |
| Moral luck | 18 |
| Norm and causation | 18 |

Ten of the 20 forms show one freezer story in its intentional version and the other in its accidental version. Six show the two greenhouse stories on opposite sides.

- **What this means.** Each pair's two versions go to different people, but each person sees both levels of almost every factor, so they can infer what is being varied. That is likely part of why the participant found the items easy.
- **Why it matters.** Kneer & Machery found that seeing both outcomes shrinks the moral-luck effect for most people, and Spranca et al. showed endings side by side deliberately, so that readers would not infer different intentions. The human run therefore estimates effects under mixed exposure, which may differ from single-vignette effects in either direction.
- **What can be checked.** The completion code records the order of items, so the data can test whether a pair's gap differs when the participant had already met the opposite side of its factor earlier in the survey.
- **For the next round:** show each person one pair per factor (5 to 10 items), or balance forms so each person sees only one side of each factor.

## 9. Making the model panel stretch human data

There are two different ways the panel can help, and they work on different units. (An earlier version of this section mixed them up; the correction came from the literature review.)

**Across pairs: prediction-powered inference.** Treat each pair as a unit. Run the panel on all N pairs and people on a random subset of n pairs, and estimate an aggregate (an author's mean human-scale score, or a factor's mean gap) as the panel's mean corrected by the average human-minus-panel difference on the human-rated subset. With the panel's weight tuned (PPI++), the variance is about σ²[(1 − ρ²)/n + ρ²/(n + N)], where ρ is the panel–human correlation across pairs. As N grows, n human-rated pairs give the precision of up to n / (1 − ρ²):

| ρ | 0.5 | 0.7 | 0.8 | 0.9 | 0.95 |
|---|---|---|---|---|---|
| Each human-rated pair worth up to | 1.3 | 2.0 | 2.8 | 5.3 | 10.3 |

The subset must be chosen at random, or with known probabilities, for the intervals to hold. Because the same people rate many pairs, standard errors should be clustered by participant.

**Within one pair: shrinkage towards the calibrated panel.** The panel gives one number per version, the same for everyone who read it, so it cannot sharpen a single pair's human mean the way it sharpens an aggregate. It can act as a prior instead. With N_p participants split evenly between versions, the human gap has variance 4σ²/N_p. If true human gaps scatter around the calibrated panel prediction with SD τ, combining the two gives the precision of N_p + 4σ²/τ² participants. With σ = 1.5, that is 36 extra participants at τ = 0.5 and 9 at τ = 1. So estimating τ from the current run, where all 30 pairs are rated by people, is the key calibration result.

**Without the panel:** each participant rates all 30 pairs, and versions are randomised independently across pairs, so adjusting each rating for the participant's mean on the other pairs is valid and reduces noise by the share of variance that is personal leniency (section 3).

## 10. Originality as a property of the set

The per-pair originality audit missed that 8 of the 20 authored pairs share a setting. Measured on the whole set instead, with settings grouped by my hand annotation (`annotations.json`), the 20 pairs contain 16 distinct settings. Their effective number, the Hill number used in ecology and equal to the Vendi score when similarity is "same setting or not", is 14.8 at order 1 and 13.3 at order 2.

Leave-one-out contributions give each pair a sign: a pair with a setting of its own adds +0.96 to the order-1 effective number, a pair that shares with one other adds −0.08, and a pair in the three-way farm-gate cluster adds −0.50. Summed by author: haiku +3.34, sonnet +2.71, opus +2.30, fable +2.30.

Two cautions. The measure is only as good as the grouping, which here is one person's reading; the literature review covers ways to make it reproducible. And effective numbers grow with set size, so only sets of equal size can be compared.

## What I would change, in order

1. **Before more people take the survey,** replace the calibration bar (section 4) and fix the analysis point (section 5). Neither changes the survey itself.
2. **Treat the human run as a calibration study, not a scoring run.** At realistic sizes it can estimate the panel's slope and per-pair error well, but not most pairs' size bins.
3. **Make leave-own-model-out the default** for authored pairs.
4. **For the next round of the benchmark:** drop or redesign the zero-entropy factors; ask for point forecasts with intervals scored by proper rules and reported as skill over the factor baseline; consider the target-size or adjudication tasks; 25 or more pairs per author; 5 to 10 items per participant with one side per factor.

## Assumptions and limits

- Human rating SD of 1.5, normal approximations for gap estimates, and no participant exclusions. Real ratings are discrete and bounded.
- "Half the panel's gaps" is a scenario from published work on model panels, not a measurement.
- The baselines in section 1 use information the authors did not have (other authors' results); they show where the score's variation comes from, not what an author could have done.
- Section 8 counts exposure in the 20 survey forms; the model panel's batches had the same issue.
