# The "cheaper fix" for the ceiling veto: tested and rejected

*26 November 2026, at the owner's request ("go ahead with the cheaper fix"). The rule and the pass criteria were committed before the test was run (commit 436ac50, `pipeline/test_ceiling_abstain.py`). Numbers are in `reports/ceiling_abstain_numbers.json` and `reports/calibration_numbers_ceiling_abstain.json`, both rebuilt by that script. The rule stays available as `--agreement-rule ceiling_abstain` in `score.py` and `pipeline/calibration/analyse.py`. It is not the default.*

## Bottom line

**The fix fails all three criteria set in advance, so the two-thirds rule stays.**

The idea was to go back to the stricter rule (three quarters of the judge models must agree on a gap's sign) but stop a model that rates both versions at the top or bottom of the scale from vetoing. It was meant to keep the strict rule's caution on human data while removing the verdict flips that the ceiling veto caused. It does neither:

| Criterion (fixed in advance) | Needed | Pilot rule | Two-thirds (current) | Ceiling abstention |
|---|---|---|---|---|
| C1. Persona panel on human data: share of confirmed gaps that people back | ≥ 50% | 55% | 39% | **41%** ✗ |
| C1. ... and human gaps it confirms | ≥ 12 | 12 | 13 | 12 ✓ |
| C2. Round 2b authored pairs whose score changes between the two panels | ≤ 2 of 27 | 5 | 1 | **5** ✗ |
| C3. Null controls confirmed in any rescored panel | 0 | 1 | 1 | **1** ✗ |

- **On the benchmark's panels it changes almost nothing.**
  - Across seven rescored panels, a judge model sat at the top or bottom of the scale on both versions for only 3 pairs.
  - The verdicts that flip between panels are mostly not ceiling vetoes: in half the split verdicts, the dissenting model is in the middle of the scale.
  - Stability is the same as under the pilot's rule: 5 score changes between round 2b's two panels, and 5.7 expected in a rerun of panel 1, against 1 and 1.7 under two-thirds.
- **On the public human data it costs nearly as much as two-thirds.**
  - MoCa's questions are yes/no, and the model judges answer them almost unanimously. A model that says "yes" (or "no") every time on both stories is at the bound, so it abstains. That happened in 72 of 85 MoCa pairs.
  - With most votes removed, MoCa's false confirmations rose from 3 to 9 (two-thirds: 10).
- **C3 fails for every rule.** The null control "weather" (+0.60, all three models agreeing) is confirmed in round 2b's panel 2 under the pilot rule, two-thirds and this rule alike. The criterion as written could not separate the rules. I should have phrased it as "no more confirmed nulls than the current rule". It doesn't change the outcome, because C1 and C2 fail on their own.

## Who vetoes, and where they sit on the scale

The fix assumed the vetoes came from Haiku at the scale's ceiling. That's true for the two classic controls, but not for most authored pairs.

Under the two-thirds rule, ten gaps in rounds 2 and 2b were confirmed with one of three models dissenting:

| Panel | Pair | Gap | Dissenting model: version A / version B | The other two |
|---|---|---|---|---|
| 2b, panel 1 | Haiku, avoidable harm 3 | +1.27 | Haiku 4.4 / 4.6 | Opus 4.4 / 3.0, Sonnet 5.4 / 2.8 |
| 2b, panel 1 | classic doing/allowing | +1.07 | Haiku 6.4 / 6.6 | Opus 6.6 / 4.2, Sonnet 5.4 / 4.4 |
| 2b, panel 2 | Haiku, avoidable harm 2 | +1.07 | Haiku 5.0 / 5.2 | Opus 5.2 / 4.2, Sonnet 5.4 / 3.0 |
| 2b, panel 2 | Haiku, luck 2 | −0.80 | Sonnet 5.0 / 5.0 | Haiku 4.8 / 5.8, Opus 4.2 / 5.6 |
| 2b, panel 2 | Opus, luck 3 | +0.73 | Haiku 6.0 / 6.0 | Opus 5.8 / 4.8, Sonnet 5.8 / 4.6 |
| 2b, panel 2 | classic doing/allowing | +0.93 | Haiku 6.4 / 6.6 | Opus 6.2 / 4.8, Sonnet 5.6 / 4.0 |
| 2b, pooled | classic luck | +0.70 | Haiku 6.6 / 6.6 | Opus 7.0 / 6.2, Sonnet 6.5 / 5.2 |
| 2b, pooled | classic doing/allowing | +1.00 | Haiku 6.4 / 6.6 | Opus 6.4 / 4.5, Sonnet 5.5 / 4.2 |
| 2 | Haiku, knowing the rule | +0.67 | Haiku 4.6 / 5.0 | Opus 5.2 / 4.6, Sonnet 5.8 / 4.0 |
| 2 | Opus, luck | +1.40 | Sonnet 3.4 / 3.4 | Haiku 6.2 / 3.4, Opus 4.8 / 3.4 |

*Mean rating per version, 1–7 scale.*

- **Haiku dissents on 8 of the 10; Sonnet on 2.**
- **The dissenter is in the top twelfth of the scale on both versions only once** (Haiku on the classic luck control, 6.6 / 6.6).
- **It is near the top four more times:** 6.4 / 6.6 on the doing/allowing control in all three round-2b panels, and 6.0 / 6.0 once.
- **Five times the dissenter sits mid-scale and simply shows no gap:** Haiku three times (4.4 to 5.2) and Sonnet twice (5.0 / 5.0 and 3.4 / 3.4). That's real disagreement, not a ceiling artefact.
- **So no threshold would have rescued the fix.** Five pairs change score between round 2b's panels under this rule:
  - three come from mid-scale dissent (Haiku's avoidable-harm pairs 2 and 3, and Sonnet dissenting on Haiku's luck pair 2);
  - one is Sonnet's luck pair, whose gap itself differs between the panels (−0.40 against −1.07), with all three models agreeing in both;
  - only one, Opus's luck pair 3 (Haiku 6.0 / 6.0), would a looser ceiling such as the top sixth have caught.

This corrects what the agreement-rule report and METHODS item 14 said on 24 November: that "the Haiku judges at the top of the scale vetoed real gaps". That holds for the two classic controls. On authored pairs, the veto was mostly a model that saw no difference.

## Human data in detail

| Panel | Rule | Gaps confirmed | ... that people show | ... where people show none | Share people back |
|---|---|---|---|---|---|
| Claude ×3, with personas (rounds 2 and 2b) | pilot | 22 | 12 | 10 | 55% |
| | two-thirds | 33 | 13 | 20 | 39% |
| | ceiling abstention | 29 | 12 | 17 | 41% |
| Claude ×3, plain | pilot | 27 | 10 | 16 | 37% |
| | two-thirds | 34 | 13 | 20 | 38% |
| | ceiling abstention | 33 | 12 | 20 | 36% |
| Claude ×4, plain (the pilot's panel) | pilot = two-thirds | 38 | 12 | 25 | 32% |
| | ceiling abstention | 40 | 13 | 26 | 33% |

*OffTheRails (60 contrasts, 1–5 scale) and MoCa (85 yes/no pairs) together.*

- **For the persona panel, on OffTheRails a model abstained on 3 of 60 contrasts.** It added one false confirmation there (7 → 8).
- **On MoCa a model abstained on 72 of 85 pairs.** Persona-panel false confirmations went from 3 to 9.

## What stays as it is

- **The two-thirds rule** (`RULES["agreement_rule"] = "two_thirds"`) and every published score.
- **The composite, the shared-pool score and the summary score.**
- **The option itself,** kept so the test can be rerun (`--agreement-rule ceiling_abstain`). Under every existing rule the outputs are byte-for-byte unchanged; this was checked for the pilot, round 2b pooled, round 2c and the persona calibration.

## What this leaves

- **The trade-off from 24 November stands.**
  - The two-thirds rule is stable between panels, but on human data its confirmations are backed by people only 39% of the time.
  - The pilot's rule is more often right (55%), but flips verdicts between panels.
  - A model that sees no gap mid-scale is a real signal, and two-thirds overrides it. The persona-panel data suggest that is where some of its false confirmations come from.
- **The remaining option from the agreement-rule report is weighting judge models by how well they track people.** It would need the same kind of pre-set test.
- **The human survey is still the only test that doesn't rest on model judges.**

## Rerun

```bash
python3 pipeline/test_ceiling_abstain.py --moral-evals <clone of cicl-stanford/moral-evals> --moca <clone of cicl-stanford/moca>
```

It takes about 10 minutes. It rescores into a temporary folder and leaves the published `out/` folders untouched.
