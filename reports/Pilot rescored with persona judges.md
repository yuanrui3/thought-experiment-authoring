# The pilot rescored with persona judges

*22 November 2026. Numbers come from `out/persona_comparison.csv` and `out/persona_comparison_summary.json`, which `pipeline/compare_persona_panel.py` rebuilds. The published results (`results.html`, `out/pair_scores.csv`) are unchanged. Fable's 10 persona judges will run once its usage limit resets on 26 November; until then the persona panel has three judge models.*

> **Update, 22 November: the prediction score changed** (see `reports/Prediction score change.md`). The numbers below were computed with the original rule. Under the new rule the persona panel still puts Fable first:
>
> | Author | Original panel, same three judge models | Persona panel | Gemini panel |
> |---|---|---|---|
> | fable | 76.1 | **74.7** | **84.7** |
> | opus | 72.4 | 72.6 | 80.1 |
> | sonnet | **81.3** | 65.3 | 73.3 |
> | haiku | 56.7 | 56.1 | 58.5 |
>
> Sonnet falls further than before. Its moral-luck pair now scores nothing under the persona panel, because its gap is no longer confirmed (under the old rule it kept half credit). *Current numbers in `out/persona_comparison_summary.json`.*

> **Update, 24 November: the agreement rule changed** (`reports/Agreement rule change.md`). A gap now needs two of three judge models to agree instead of all three; with four models nothing changes. On the persona panel, Sonnet's moral-luck pair is now confirmed and Sonnet rises from 65.3 to 73.3. Fable stays first, narrowly (74.7). The numbers in this report's body are under the old rule; `--agreement-rule three_quarters` rebuilds them.

## Bottom line

On the public human data, giving each judge a participant persona made the model panel behave more like people (see `reports/Fixing the panel's overconfidence.md`). Rerunning the pilot that way gives this:

- **6 of the 30 verdicts change**, 4 of them on authored pairs. Effects keep the same order: their correlation with the original panel is 0.98.
- **First place moves from Sonnet to Fable,** the same direction the Gemini panel pointed. Sonnet loses the most: its doing-vs-allowing pair loses its gap, and its moral-luck pair is no longer confirmed.

  | Author | Original panel, same three judge models | Persona panel | Gemini panel |
  |---|---|---|---|
  | fable | 76.7 | **76.7** | **84.7** |
  | opus | 72.6 | 74.6 | 78.7 |
  | sonnet | **81.3** | 71.3 | 75.3 |
  | haiku | 63.7 | 65.5 | 65.7 |

  *Mean composite score, 0–100.*
- **The two pairs that decided first place now agree in one respect: neither shows a gap.** On Sonnet's doing/allowing pair, the persona panel sides with Gemini. On Fable's norm-violation pair, it sides with the original Claude panel. So Sonnet loses its hit and Fable gains nothing.
- **The persona panel confirms fewer small effects.** It loses the classic moral-luck control, a known small human effect (gap 0.53 → 0.13), so 4 of 5 classic controls now show their expected direction instead of 5. That matches the calibration, where personas cut confirmations from 21 to 15.
- **None of this is people.** The calibration showed persona panels are closer to people but still about half wrong on the gaps they confirm. The ranking is still a ranking against model judges.

## What was run

- **Judges:**
  - Haiku, Sonnet and Opus, 10 judges each: 5 repeats × 2 arms of 30 vignettes.
  - Same batches, versions and order as the original panel (`pipeline/batches.json`).
  - One persona per judge, drawn with a fixed seed by `pipeline/calibration/personas.py`; recorded in `pipeline/batches_persona.json`.
- **Prompt:** the original judge prompt word for word (checked character by character), plus one closing paragraph saying the "structured answer" is a JSON file to write. The persona came first, as in the calibration.
- **Delivery differs from the original panel in two ways,** so the comparison isn't purely about personas:
  - the original judges got the prompt inline at effort "low" and answered through a structured-output tool;
  - the persona judges read it from a file at the default effort and wrote a JSON file.

  The calibration test, where both conditions used the same delivery, is the clean measure of what personas do. This rerun applies them to the pilot.
- **Storage:** run `persona` in `judgments.csv` (protocol `panel-v1-persona`). Answers are in `pipeline/raw/panel_persona/` and provenance in `pipeline/raw/panel_persona_provenance.json`.
- **Scoring:** same rules and the same audits. The comparison panel is the original run restricted to the same three judge models. With three judge groups, a gap is confirmed only if all three models agree in sign. That applies to both panels equally; the published four-model panel needed three of four.
- **Provenance:**
  - All 30 judges were served the requested model, read their own file, and wrote their own answers.
  - Three Haiku judges made one more call after writing: twice loading a tool definition, once looking up product documentation. None wrote anything afterwards, so their answers stand.
  - All 30 got the same share of factual questions right as the original judges (99.3%).

## What changed

**Spread of ratings within one version of a story, one model** (1–7 scale):

| Judge model | Original | With personas |
|---|---|---|
| Haiku | 0.54 | 0.58 |
| Sonnet | 0.41 | 0.49 |
| Opus | 0.19 | 0.40 |

Opus, the most deterministic judge, doubles; Haiku, already the noisiest, barely moves. Mean |gap| on authored pairs falls from 1.90 to 1.77 points.

**The six verdicts that change:**

| Pair | Predicted | Original (3 models) | Persona panel | Gemini | Prediction score, original → persona |
|---|---|---|---|---|---|
| Sonnet, doing vs allowing | A higher, small | A higher, small (+0.73, 3/3) | no difference (+0.27) | no difference (+0.10) | 1.0 → 0.25 |
| Sonnet, moral luck | B higher, small | B higher, small (−0.80, 3/3) | not confirmed (−0.53, 2/3 agree) | B higher, small | 1.0 → 0.5 |
| Haiku, doing vs allowing | A higher, small | B higher, small (−0.93) | no difference (−0.47) | not confirmed (−0.50) | 0 → 0.25 |
| Opus, norm violation → cause | A higher, large | A higher, small (+1.47) | A higher, large (+2.13) | A higher, large (+3.80) | 0.75 → 1.0 |
| Classic control, moral luck | A higher, small | A higher, small (+0.53) | no difference (+0.13) | A higher, small (+1.40) | 1.0 → 0.25 |
| Classic control, norm violation | A higher, large | A higher, small (+1.47) | A higher, large (+1.60) | A higher, large (+2.30) | 0.75 → 1.0 |

*Gaps are mean rating of version A minus version B, on the 1–7 scale; "3/3" means all three judge models agreed in sign.*

**The four pairs where the vendors disagreed** (identified in `reports/Pilot rescored with Gemini.md`):

| Pair | Predicted | Original (3 models) | Persona panel | Gemini |
|---|---|---|---|---|
| Sonnet, doing vs allowing | A higher, small | A higher, small | **no difference** | no difference |
| Fable, norm violation → cause | A higher, small | no difference (+0.07) | **no difference** (+0.20) | A higher, small (+1.40) |
| Opus, doing vs allowing | A higher, small | no difference (+0.20) | no difference (+0.33) | A higher, small (+0.50) |
| Haiku, norm violation → cause | A higher, small | A higher, large (+1.93) | A higher, large (+1.67) | A higher, small (+1.40) |

- **The persona panel agrees with Gemini's verdict on 21 of 30 pairs;** the original panel did on 20.
- **It doesn't settle the swing pairs.** It sides with Gemini on one and with the original Claude panel on the other three.
- **Three of these four pairs are now "no difference" under at least two of the three panels.** Most of the disagreement is about small effects that model panels may or may not detect.

## What this means

1. **The pilot's winner is panel-dependent, and two of three panels now put Fable first.** The pilot can report "Fable or Sonnet" rather than Sonnet. What's robust is lower down: Haiku is last under every panel, and Opus sits in the middle.
2. **Persona judges are more conservative about small effects.** That fits the calibration, where they cut false confirmations. It also costs real effects: the classic moral-luck control, which people do show, disappears here. On balance the calibration favoured personas; the lost classic control is the price.
3. **The survey's target pairs stay the same.** Sonnet's and Opus's doing/allowing pairs, and Fable's and Haiku's norm-violation pairs, are still where human data would decide the ranking.
4. **Use persona judges from now on, with all four models once Fable's limit resets.** The reminder set for 26 November now covers Fable's 10 persona judges as well.

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
