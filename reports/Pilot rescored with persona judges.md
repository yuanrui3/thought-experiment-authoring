# The pilot rescored with persona judges

*Numbers come from `out/persona_comparison.csv` and `out/persona_comparison_summary.json`, which `pipeline/compare_persona_panel.py` rebuilds. The published results (`results.html`, `out/pair_scores.csv`) are unchanged. First written 22 November 2026 with three judge models; rewritten 26 November, when Fable's 10 persona judges ran after its usage limit reset. All numbers below use the current rules: the distance prediction score (22 November) and the two-thirds agreement rule (24 November), under which four judge models need 3 of 4 to agree.*

## Bottom line

On the public human data, giving each judge a participant persona made the model panel behave more like people (see `reports/Fixing the panel's overconfidence.md`). Here the pilot is rejudged that way by all four judge models, and compared with the published four-model panel.

- **3 of the 30 verdicts change,** 2 of them on authored pairs. Effects keep the same order: their correlation with the published panel is 0.99.
- **First place moves from Sonnet to Fable,** the same direction the Gemini panel pointed. Sonnet loses its doing-vs-allowing pair, whose gap disappears under personas, as it does under Gemini.

  | Author | Published panel (4 models) | Persona panel (4 models) | Gemini panel |
  |---|---|---|---|
  | fable | 76.7 | **75.1** | **84.7** |
  | sonnet | **81.3** | 73.3 | 73.3 |
  | opus | 72.6 | 72.6 | 80.1 |
  | haiku | 56.6 | 56.5 | 58.5 |

  *Mean composite score, 0–100.*
- **Fable's lead under personas is narrow** (75.1 against 73.3). The order below Fable is Sonnet, then Opus, then Haiku.
- **The persona panel confirms fewer small effects.** It loses the classic moral-luck control, a known small human effect: the gap falls from 0.60 to 0.40 and only 2 of 4 models agree. So 4 of 5 classic controls reproduce instead of 5. That matches the calibration, where personas cut false confirmations but also missed some real small effects.
- **None of this is people.** The calibration showed persona panels are closer to people but still about half wrong on the gaps they confirm. The ranking is still a ranking against model judges.

## What was run

- **Judges:**
  - Haiku, Sonnet, Opus and Fable, 10 judges each: 5 repeats × 2 arms of 30 vignettes.
  - Same batches, versions and order as the published panel (`pipeline/batches.json`).
  - One persona per judge, drawn with a fixed seed by `pipeline/calibration/personas.py`; recorded in `pipeline/batches_persona.json`.
  - Haiku, Sonnet and Opus ran on 22 November and Fable on 26 November. Everything else was identical, including the files they read.
- **Prompt:** the original judge prompt word for word (checked character by character), plus one closing paragraph saying the "structured answer" is a JSON file to write. The persona came first, as in the calibration.
- **Delivery differs from the published panel in two ways,** so the comparison isn't purely about personas:
  - the original judges got the prompt inline at effort "low" and answered through a structured-output tool;
  - the persona judges read it from a file at the default effort and wrote a JSON file.

  The calibration test, where both conditions used the same delivery, is the clean measure of what personas do. This rerun applies them to the pilot.
- **Storage:** run `persona` in `judgments.csv` (protocol `panel-v1-persona`). Answers are in `pipeline/raw/panel_persona/` and provenance in `pipeline/raw/panel_persona_provenance.json`.
- **Scoring:** same rules and the same audits as the published panel.
- **Provenance:**
  - All 40 judges were served the requested model, read their own file, and wrote their own answers.
  - Three Haiku judges made one more call after writing: twice loading a tool definition, once looking up product documentation. None wrote anything afterwards, so their answers stand.
  - Judges got 99.5% of factual questions right, the same as the published panel.

## What changed

**Spread of ratings within one version of a story, one model** (1–7 scale):

| Judge model | Published | With personas |
|---|---|---|
| Haiku | 0.54 | 0.58 |
| Sonnet | 0.41 | 0.49 |
| Opus | 0.19 | 0.40 |
| Fable | 0.19 | 0.48 |

- **The two most deterministic judges, Opus and Fable, more than double.**
- **Haiku, already the noisiest, barely moves.**
- **Mean gap on authored pairs** falls from 2.0 to 1.8 points.

**The three verdicts that change:**

| Pair | Predicted | Published (4 models) | Persona panel | Gemini | Prediction score, published → persona |
|---|---|---|---|---|---|
| Sonnet, doing vs allowing | A higher, small | A higher, small (+0.75, 4/4) | no difference (+0.30) | no difference (+0.10) | 1.0 → 0 |
| Haiku, doing vs allowing | A higher, small | B higher, small (−0.80, 4/4) | no difference (−0.35) | not confirmed (−0.50) | 0 → 0 |
| Classic control, moral luck | A higher, small | A higher, small (+0.60, 4/4) | no difference (+0.40, 2/4) | A higher, small (+1.40) | 1.0 → 0 |

*Gaps are mean rating of version A minus version B, on the 1–7 scale; "4/4" means all four judge models agreed in sign.*

**The four pairs where the vendors disagreed** (identified in `reports/Pilot rescored with Gemini.md`):

| Pair | Predicted | Published (4 models) | Persona panel | Gemini |
|---|---|---|---|---|
| Sonnet, doing vs allowing | A higher, small | A higher, small | **no difference** | no difference |
| Fable, norm violation → cause | A higher, small | no difference (+0.35) | no difference (+0.40) | A higher, small (+1.40) |
| Opus, doing vs allowing | A higher, small | no difference (+0.20) | no difference (+0.30) | A higher, small (+0.50) |
| Haiku, norm violation → cause | A higher, small | A higher, large (+1.90) | A higher, large (+1.65) | A higher, small (+1.40) |

- **Both panels agree with Gemini's verdict on 22 of 30 pairs.**
- **The persona panel doesn't settle the swing pairs.** It sides with Gemini on Sonnet's doing-vs-allowing pair and with the published Claude panel on the other three.
- **Three of these four pairs are "no difference" under at least two of the three panels.** Most of the disagreement is about small effects that model panels may or may not detect.

## With three judge models (22 November)

Before Fable's judges ran, the persona panel had Haiku, Sonnet and Opus only. It was compared with the published panel restricted to those three models.

- Under the current rules, 5 verdicts changed in that comparison, 3 of them on authored pairs (6 under the rules first used on 22 November).
- The three-model panel gave Fable 74.7, Sonnet 73.3, Opus 72.6 and Haiku 56.1, so Fable led there too.
- With four models on both sides, two of those changes disappear. Opus's norm-violation pair and the classic norm-violation control are "large" under both panels.
- The author order did not change.

## What this means

1. **The pilot's winner is panel-dependent, and two of three panels put Fable first.** The pilot can report "Fable or Sonnet" rather than Sonnet. What's robust is lower down: Haiku is last under every panel, and Opus sits in the middle.
2. **Persona judges are more conservative about small effects.** That fits the calibration, where they cut false confirmations. It also costs real effects: the classic moral-luck control, which people do show, isn't confirmed here. On balance the calibration still favours personas.
3. **The survey's target pairs stay the same.** Sonnet's and Opus's doing-vs-allowing pairs, and Fable's and Haiku's norm-violation pairs, are where human data would decide the ranking.
4. **Persona judges are the panel used from round 2 on.** Round 2c will be the first round with all four models judging as personas from the start.

## Rerun

```bash
python3 pipeline/persona_panel.py build --out pj --answers pja
```

Then, for each batch in `pipeline/batches_persona.json`, start a fresh agent of that model with the recorded persona and instruction: read `pj/<batch>.txt`, write `pja/<batch>.json`. Copy the answers into `pipeline/raw/panel_persona/`.

```bash
python3 pipeline/persona_panel.py check --transcripts <subagent transcript dir> --answers pipeline/raw/panel_persona
```

```bash
python3 pipeline/persona_panel.py ingest --answers pipeline/raw/panel_persona
```

```bash
python3 pipeline/compare_persona_panel.py
```
