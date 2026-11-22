# The pilot rescored with Gemini as a second judge group

*22 November 2026. Numbers come from `out/vendor_comparison.csv` and `out/vendor_comparison_summary.json`, which `pipeline/compare_vendor_panels.py` rebuilds. The pilot's own scores (`out/pair_scores.csv`, and every section of `results.html` above the new one) are unchanged and remain the Claude panel's. `results.html` now has a section, "A second judge panel: Gemini", that shows this comparison side by side.*

## Bottom line

**The two vendors broadly agree, but not on the pairs that decide which author comes first.**

**Where they agree:**
- The direction of the gap on 26 of 30 pairs.
- Which pairs have larger effects: the correlation of effects across pairs is 0.94.
- Every null control shows no gap, and every classic control shows its known direction.
- Both got every factual question right.

**Where they differ:** 8 of 30 verdicts on direction and size, 7 of them on authored pairs. Mostly these are small effects near the 0.5-point threshold. Doing vs allowing accounts for four of the eight (three authored pairs and the classic control).

**The author ranking depends on the panel.** Treating the two vendors as two judge groups, the "second judge group" asked for, moves the ranking:

| Author | Claude panel (as published) | Gemini panel | Two judge groups: Claude + Gemini |
|---|---|---|---|
| fable | 76.7 | **84.7** | **84.7** |
| sonnet | **81.3** | 75.3 | 75.3 |
| opus | 74.6 | 78.7 | 74.6 |
| haiku | 63.7 | 65.7 | 63.7 |

*Mean composite score, 0–100.*

Two pairs cause the swing:
- **Sonnet's doing-vs-allowing pair.** Claude finds the small gap Sonnet predicted; Gemini finds none.
- **Fable's norm-violation pair.** Claude finds no gap; Gemini finds the small gap Fable predicted.

**Which reading is more likely right?** On the public human data, when one vendor confirmed a gap and the other didn't, people backed the Claude-only gaps 0 times out of 9 and the Gemini-only gaps 16 times out of 26 (across both datasets). That leans toward Gemini's reading of both swing pairs, and so toward Fable first. But those were different stories and small counts. Only human ratings of these pairs can settle it.

**Report the pilot's winner as "Sonnet or Fable, depending on the judge panel".**

## Judgment calls

1. **Two Gemini models:** `gemini-4-argon` (Google's flagship) and `gemini-3-flash-preview` (a cheap tier). The same pair also took part in the calibration.
2. **Same design as the Claude panel.**
   - For each model: 5 repeats × 2 arms, so 10 batches of 30 vignettes. Each batch holds one version of every pair, never both, in its own random order.
   - The randomisation is separate from the Claude panel's (seed 20261122) and is saved in `pipeline/batches_gemini.json`.
3. **Same prompt, word for word.** I checked it by rendering a Claude judge's prompt from the pilot's own workflow script and comparing character by character: identical.
   - Reasoning effort "low", as for the Claude judges.
   - One difference: the Claude judges answered through a structured-output tool. Gemini got one API call per batch, with a system message saying the "structured answer" is a JSON object, and a request for JSON matching the same schema. All 20 calls returned valid answers on the first try.
4. **Stored as run `gemini` in `judgments.csv`,** with protocol `panel-v1-api`.
   - Every existing script selects rows by run, so the published results are untouched. `score.py` still reproduces `out/` and `results.html` byte for byte.
5. **Audits unchanged.** Confound and originality ratings still come from the pilot's Claude auditors (`score.py --audit-run main`). Only the judgments change.
6. **"Two judge groups" scoring:**
   - each vendor's ratings are pooled into one group;
   - the effect is the mean of the two vendors' effects;
   - under `score.py`'s rule (at least 75% of groups agree in sign), a gap counts only if both vendors agree.

   For completeness, the comparison also reports each vendor alone and all six models as six equal groups.
7. **Cost.** $0.47 on the spending ledger, which counts double the listed prices, so about $0.23 at list. All Gemini work so far totals $2.45 on the ledger, about $1.22 at list, inside the $5 budget.

## Where the vendors disagree

| Pair | Predicted | Claude panel | Gemini panel | Two judge groups | Prediction score: Claude / Gemini / two groups |
|---|---|---|---|---|---|
| Sonnet, doing vs allowing | A higher, small | A higher, small (+0.75) | none (+0.10) | none (+0.43) | 1.0 / 0.25 / 0.25 |
| Fable, norm violation → cause | A higher, small | none (+0.35) | A higher, small (+1.40) | A higher, small (+0.88) | 0.25 / 1.0 / 1.0 |
| Opus, doing vs allowing | A higher, small | none (+0.20) | A higher, small (+0.50) | none (+0.35) | 0.25 / 1.0 / 0.25 |
| Haiku, doing vs allowing | A higher, small | B higher, small (−0.80) | unclear (−0.50; models split) | B higher, small | 0 / 0 / 0 |
| Haiku, norm violation → cause | A higher, small | A higher, large (+1.90) | A higher, small (+1.40) | A higher, large | 0.75 / 1.0 / 0.75 |
| Opus, moral luck | A higher, large | A higher, large (+1.85) | A higher, small (+1.40) | A higher, large | 1.0 / 0.75 / 1.0 |
| Fable, moral luck | B higher, large | B higher, small (−1.50) | B higher, large (−1.80) | B higher, large | 0.75 / 1.0 / 1.0 |
| Classic control, doing vs allowing | A higher, small | A higher, small (+1.15) | A higher, large (+1.90) | A higher, large | 1.0 / 0.75 / 0.75 |

*Effects are mean rating of version A minus version B, on the 1–7 scale.*

- **Doing vs allowing is the least stable factor across vendors.**
  - Of its four authored pairs, the vendors disagree on three.
  - They also disagree on the size of the classic control, where Gemini calls the known small effect large.
  - The calibration already showed neither vendor is reliable on small doing/allowing effects.
- **The size disagreements sit at the 1.5-point line between "small" and "large".** Gemini's effects on authored pairs are larger on average (mean |effect| 2.44 against Claude's 2.00), consistent with the calibration, where Gemini exaggerated sizes more. Size scores therefore partly reflect which panel is used.

## Authors under each scoring

| Author | Scoring | Mean composite | Mean prediction score | Full hits (of 5) |
|---|---|---|---|---|
| fable | Claude / Gemini / two groups / six models | 76.7 / 84.7 / 84.7 / 80.7 | 0.80 / 1.00 / 1.00 / 0.90 | 3 / 5 / 5 / 4 |
| sonnet | Claude / Gemini / two groups / six models | 81.3 / 75.3 / 75.3 / 81.3 | 1.00 / 0.85 / 0.85 / 1.00 | 5 / 4 / 4 / 5 |
| opus | Claude / Gemini / two groups / six models | 74.6 / 78.7 / 74.6 / 74.6 | 0.85 / 0.95 / 0.85 / 0.85 | 4 / 4 / 4 / 4 |
| haiku | Claude / Gemini / two groups / six models | 63.7 / 65.7 / 63.7 / 63.7 | 0.65 / 0.70 / 0.65 / 0.65 | 1 / 2 / 1 / 1 |

- **Haiku is last under every scoring.**
- **The top place depends on the panel.**
  - Fable leads under Gemini and under the two-vendor scoring.
  - Sonnet leads under Claude and when all six models count equally. Four of those six are Claude, so that scoring mostly repeats Claude's verdicts.
- **No sign of a panel favouring its own vendor's authors.** All four authors are Claude models, and the Claude panel helps one Claude author (Sonnet) and hurts another (Fable).

## Other checks

- **Factual questions:** both Gemini models answered all 300 correctly. The Claude models scored 98–100%.
- **Spread of ratings for one version of a story:**
  - Within one model: 0.28 (Argon) and 0.40 (Flash), against 0.19–0.54 for the Claude models.
  - Pooled by vendor: Gemini 0.45, Claude 0.73.

  Either way, much less than the spread among people in the calibration datasets. The confidence intervals here are therefore just as narrow as the Claude panel's, and "interval excludes zero" means little.
- **Provenance:** all 20 calls were served by the model requested, and every answer is saved in `pipeline/raw/panel_gemini/`.

## What this means

1. **Don't publish a single winner from model judges.** The pilot's ranking holds at the bottom (Haiku) but not at the top. The deciding pairs are small effects near the threshold, which is exactly where the calibration found model panels least reliable.
2. **Point the human survey at the swing pairs.** These have the most leverage on the result:
   - Sonnet's doing/allowing and Fable's norm-violation pairs, which decide first place;
   - Opus's doing/allowing pair, and Haiku's norm-violation pair (the small/large boundary).

   Small effects need many people per version (see the mathematical analysis), so a survey aimed at these four pairs gets more out of each participant than one spread over all 30.
3. **If model verdicts are shown, show each vendor's side by side.**
   - On public human data, requiring both vendors to agree did not make verdicts more trustworthy: people backed 8 of 19 such gaps.
   - Averaging all six models just repeats Claude's verdicts.

## Rerun

```bash
python3 pipeline/api_panel.py build --aliases argon=gemini-4-argon flash=gemini-3-flash-preview
```

```bash
python3 pipeline/api_panel.py run --alias argon --price-in 4 --price-out 20 --cap 4.50
```

```bash
python3 pipeline/api_panel.py run --alias flash --price-in 1 --price-out 6 --cap 4.50
```

```bash
python3 pipeline/api_panel.py ingest
```

```bash
python3 pipeline/compare_vendor_panels.py
```

`build` refuses to overwrite the saved manifest, and `run` skips batches that already have answers. So rerunning only the last two commands rebuilds every number here from the saved answers, with no API calls. The API calls need a Gemini key: the session's network proxy supplied it here; elsewhere, set `GEMINI_API_KEY`.
