# Fixing the panel's overconfidence: personas and sampling noise

*22 November 2026. Numbers come from `reports/calibration_numbers_persona_noise.json`, built by `pipeline/calibration/analyse.py` from the answers in `pipeline/calibration/answers_persona/` and `pipeline/calibration/answers_gemini/`.*

## Bottom line

Model judges barely vary between repeats. Within one version of a story, a single Claude model's ratings have an SD of 0.17–0.18 on the 1–5 scale; people's are 0.79–1.03. I tested two cheap fixes on the same public human data as the calibration:

- **Personas:** each judge answers as a described participant.
- **Sampling noise:** Gemini run at temperature 2 instead of its default.

**Personas help; turning up the temperature doesn't.**

1. **Personas double each model's spread and improve calibration.** For the three Claude models:
   - false positives fall from 12 to 7 of the 40 contrasts where people show no gap;
   - people back 8 of 15 confirmed gaps instead of 8 of 21 (53% instead of 38%);
   - people's gap falls inside the panel's interval 44 times in 60 instead of 35;
   - the correlation with people rises from 0.47 to 0.52, and on the intention question from −0.18 to +0.16;
   - the spread of human gaps around the panel's gaps (τ) shrinks from 0.61 to 0.49 on the 1–7 scale.

   For Gemini Flash, personas raise coverage from 40 to 49 and cut τ from 0.45 to 0.37. They also lower its correlation with people (0.72 to 0.59) and its hits (14 to 10).
2. **Temperature 2 barely changes anything.** Flash's spread goes from 0.28/0.44 (permissibility/intention) to 0.30/0.48, and every calibration measure stays within a contrast or two.
3. **Personas plus temperature give the most spread** (0.68/0.76, closest to people's 0.79/1.03) but no better verdicts than personas alone.
4. **It still isn't people.** With personas:
   - spread stays below people's;
   - the panel still sees a gap between the means and side-effect stories 3–8 times larger than people's;
   - at best about half of confirmed gaps are backed by people.

**What to do:** use personas whenever a model panel judges, because they cost nothing and help. Don't bother with temperature. Don't treat persona-panel verdicts as people's.

## Design

| | Claude | Gemini 3 Flash |
|---|---|---|
| Judges | Haiku, Sonnet, Opus: 10 each, the same batches (b01–b30) each model judged in the calibration | 40, all calibration batches |
| Conditions | Original (from the calibration) vs personas | Original vs personas vs temperature 2 vs both |
| Cost | Session sub-agents, no API spend | About $0.60 at list prices for the three new runs |

- **Fable left out.** Its usage limit had been hit, so the Claude comparison uses three models: the original three-model panel against the same three with personas.
- **Personas** come from `pipeline/calibration/personas.py` (fixed seed), one per batch: age, gender, US region, job, education, politics, religiosity, reading habit and rating-scale habit. The weights are rough guesses for an online US sample, and simple rules rule out implausible combinations. Nothing in a persona mentions the study. The scale-use habits are meant to supply the person-to-person variation real samples have: picking the middle, picking the ends, tending to agree, tending to disagree.
- **Judge instructions:** the same as in the calibration, with the persona put first and "answer as this person honestly would: people differ, and there are no right or wrong answers".
- **One run of each condition.** A difference of two or three contrasts between conditions is within what a rerun could produce. The changes in spread, coverage and τ are larger and appear for both vendors.

## Results: OffTheRails, 60 contrasts

| Panel | Rating SD, perm. / int. (people 0.79 / 1.03) | Within one model | People's gap inside the panel's interval (of 60) | Confirmed | Backed by people | False positives (of 40) | r with people | r, intention | τ (1–7 scale) |
|---|---|---|---|---|---|---|---|---|---|
| Claude ×3 | 0.43 / 0.31 | 0.17 / 0.18 | 35 | 21 | 8 | 12 | 0.47 | −0.18 | 0.61 |
| Claude ×3, personas | 0.57 / 0.44 | 0.34 / 0.24 | **44** | 15 | 8 | **7** | 0.52 | 0.16 | **0.49** |
| Flash | 0.28 / 0.44 | 0.28 / 0.44 | 40 | 29 | 14 | 15 | **0.72** | 0.38 | 0.45 |
| Flash, personas | 0.59 / 0.66 | 0.59 / 0.66 | **49** | 21 | 10 | **11** | 0.59 | 0.16 | **0.37** |
| Flash, temperature 2 | 0.30 / 0.48 | 0.30 / 0.48 | 43 | 32 | 16 | 16 | 0.72 | 0.44 | 0.45 |
| Flash, personas + temp. 2 | 0.68 / 0.76 | 0.68 / 0.76 | 44 | 26 | 13 | 13 | 0.61 | 0.32 | 0.52 |

- **What a well-behaved panel would score on coverage.** A panel with these interval widths and no bias would contain people's gap about 52–55 times in 60. That's short of 60 because people's own gaps are estimates with noise. So the original panels fall 12–17 short of an unbiased panel, and with personas 6–10 short.
- **The pilot rule's precision** (people back what the panel confirms) is 38% for Claude and 53% with personas. Flash stays near 50% whatever is changed.

**Bias in the main effects** (mean gap on the 1–5 scale):

| Contrast | People | Claude ×3 | with personas | Flash | with personas | temp. 2 | personas + temp. 2 |
|---|---|---|---|---|---|---|---|
| means − side effect (different stories), permissible | −0.07 | −0.73 | −0.53 | −0.51 | −0.40 | −0.49 | −0.62 |
| means − side effect, intended | +0.20 | +0.76 | +0.56 | +0.50 | +0.60 | +0.66 | +0.61 |
| avoidable − unavoidable, intended | +0.34 | +0.09 | +0.15 | +0.48 | +0.35 | +0.44 | +0.38 |
| acts − does not prevent, permissible | +0.11 | −0.10 | −0.06 | −0.07 | +0.01 | −0.13 | −0.11 |

- **Personas narrow the biggest bias but don't remove it.** Claude's means/side-effect gap shrinks by about a quarter.
- **On acting vs not preventing,** Flash with personas is the only panel whose permissibility gap points the same way as people's, and only just (+0.01).
- **Average ratings move toward people's.** Flash's mean permissibility goes from 4.45 to 4.16 (people 4.07) and its mean intention from 1.47 to 1.84 (people 2.20). Claude's barely move.

## Results: MoCa, 85 pairs

| Panel | r with people | Where people differ by ≥ 0.30 (34): same / no gap / opposite | Hits / false positives |
|---|---|---|---|
| Claude ×3 | 0.17 | 32% / 44% / 24% | 2 / 4 |
| Claude ×3, personas | 0.24 | 32% / 56% / 12% | 4 / 3 |
| Flash | 0.38 | 38% / 56% / 6% | 7 / 7 |
| Flash, personas | 0.36 | **53%** / 41% / 6% | **11** / 7 |
| Flash, temperature 2 | 0.37 | 53% / 41% / 6% | 6 / 5 |
| Flash, personas + temp. 2 | 0.36 | 53% / 41% / 6% | 9 / 6 |

- **Claude:** personas halve the opposite-direction answers.
- **Flash:** personas raise hits from 7 to 11 with no extra false positives.
- **Correlation:** none of the changes moves it much on this dataset.

## What this means for the benchmark

1. **Give every panel judge a persona.** It's free, it doubles the spread, and for Claude it improved every calibration measure here. The pilot's panel judges had none. Rescoring the pilot with persona judges is the next cheap step: about 40 sub-agent runs, no API cost.
2. **Don't rely on temperature.** At least for Gemini, more sampling noise doesn't create person-to-person variation.
3. **A persona panel makes a better prior.**
   - Using the formula in the mathematical analysis (a prior worth 4σ²/τ² participants per pair, with σ ≈ 1.45 on the 1–7 scale), Flash with personas (τ 0.37) would be worth about 60 participants per pair. Claude with personas (τ 0.49) would be worth about 35, against about 23 for the original Claude panel.
   - These figures assume the calibration carries over to the pilot's stories, and part of τ is bias that a calibration slope would only partly remove.
   - They still don't make panel verdicts a substitute for people.
4. **The pilot's verdict rule remains the weak point.** Even the best panel here gets only about half its confirmed gaps backed by people. The survey, aimed at the pairs where the panels disagree, is still what settles the authored pairs.

## Notes

- **Stray tool calls.** Three Haiku persona judges made a tool call after writing their answers: one tried to message another session (it failed for lack of an address), and two tried to start a new session (the permission system blocked both). None could have seen anything that changed its answers, so all 30 count as usable. Provenance is in `pipeline/calibration/provenance_persona.json`. This is the third time Haiku judges have reached for session tools. Future runs should use a judge agent type that has only Read and Write.
- **Gemini spending to date:** $3.62 on the ledger, which counts double the listed prices, so about $1.81 at list.

## Rerun

```bash
python3 pipeline/calibration/personas.py
```

```bash
python3 pipeline/calibration/run_api_judge.py --model gemini-3-flash-preview --batches jb --out pipeline/calibration/answers_gemini/gemini-3-flash-preview-persona --personas pipeline/calibration/personas.json --condition persona --price-in 1 --price-out 6 --cap 4.50 --ledger pipeline/calibration/api_ledger.jsonl
```

For the other two Gemini conditions, repeat the command with `--temperature 2.0`, with and without `--personas`, and a matching `--out`. The Claude persona judges got the calibration judge prompt with the persona text in front; their answers are in `pipeline/calibration/answers_persona/`.

To score any condition, add `--group <label>=<answers folder>` for each set of answers and `--panel <labels>` to the calibration analysis command in `reports/Calibration on public human data.md`.

```bash
python3 pipeline/calibration/check_judges.py --transcripts <subagent transcript dir> --answers <persona answers> --writes-to jp
```
