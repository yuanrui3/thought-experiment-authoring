#!/usr/bin/env python3
"""More ratings per judge model: round 2c judged by a second, independent persona panel, pooled to 20 ratings per
model and version; plus the first check of the four-model persona panel against people.

    python3 pipeline/round2/analyse_c_panels.py --moral-evals DIR --moca DIR

Requested by the owner on 26 November 2026 ("go ahead with more ratings per judge model"). This file, with the second
panel's manifest (pipeline/round2/judge_batches_c_p2.json, seed 20261129, new personas), was committed BEFORE any of
the new judges ran. The measures and criteria below are fixed here.

DATA
  round2c-p2  80 persona judges (Fable, Opus, Sonnet, Haiku x 10 repeats x 2 arms) on the same 46 items, a new seed and
              new personas. Together with round2c: 20 ratings per model and version.
  Fable's 10 persona judges on the public human data (calibration batches b31-b40 with personas b31-b40 of
  pipeline/calibration/personas.json, the prompt the other persona judges had). This is the first calibration of the
  four-model persona panel that round 2c uses. With four models, two-thirds and three-quarters both mean 3 of 4.

Score first (current rules):
    python3 score.py --vignettes round2/vignettes_c.json --run round2c-p2 --audit-run main,round2,round2b,round2c --out out/round2c_p2 --no-report
    python3 score.py --vignettes round2/vignettes_c.json --run round2c,round2c-p2 --audit-run main,round2,round2b,round2c --out out/round2c_pooled --no-report

MEASURES
  1. Panel 1 against panel 2 (46 items): effect correlation, mean absolute difference, noise ratio (sum of squared gap
     differences over the sum of both squared standard errors), verdict changes, and authored pairs whose prediction
     score changes by more than 0.25.
  2. Judge-level resampling (whole repeats within each judge model; 300 resamples, 400 inner bootstrap draws), for
     panel 1 alone (10 ratings per model and version) and for the pooled panel (20): the expected number of authored
     scores that change by more than 0.25 in a rerun, the spread of each author's mean prediction score, and how often
     each author is first.
  3. Authors on the pooled panel: composite and prediction score, against each panel alone.
  4. The four-model persona panel on the human data, all 10 judges per model, against 20 random halves (5 judges per
     model; seed 20261129): confirmed gaps, how many people back, share backed.

CRITERIA for making 20 ratings per model and version (two independent panels, pooled) the standard for later rounds
  C1 stability. The pooled panel's expected score changes per rerun are at most half of panel 1's. (In round 2b,
     pooling cut them from 1.7 to 0.7 under two-thirds, and from 5.7 to 2.6 under three-quarters.)
  C2 no validity cost. On the human data, the share of confirmed gaps backed by people with 10 judges per model is at
     most 5 percentage points below the mean share with 5. This is the best available sign of what doubling does,
     since no 20-judge calibration exists.
  If both pass: 20 ratings per model and version becomes the standard. If C1 fails, doubling doesn't buy enough
  stability for its cost. If C2 fails, more ratings make the panel confirm more gaps that people don't show.

WHATEVER THE OUTCOME
  Round 2c's headline numbers become the pooled panel's. The shared-pool score's target is "all of the round's panels
  pooled" by definition, and the composite and summary follow it, as round 2b's pooled panels did.

Writes reports/round2c_panels_numbers.json and reports/calibration_numbers_persona4.json.
"""
import argparse, csv, json, os, random, shutil, statistics, subprocess, sys, tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
import score  # noqa: E402

CAL = os.path.join(ROOT, "pipeline", "calibration")
MODELS = ["haiku", "sonnet", "opus", "fable"]


def pairs_csv(d):
    return {r["pair_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, d, "pair_scores.csv"), encoding="utf-8"))}


def f(x):
    return float(x)


def se(r):
    return (f(r["ci_high"]) - f(r["ci_low"])) / (2 * 1.96)


def resample(runs, V, todo, n_outer, n_inner, rng):
    rows = score.load_judgments(os.path.join(ROOT, "judgments.csv"), ",".join(runs))
    units = {}
    for r in rows:
        units.setdefault((r["run_id"], r["judge_group"], r["repeat"]), {}).setdefault(r["pair_id"], {}).setdefault(r["version"], []).append(r["rating"])
    groups = sorted({u[1] for u in units})
    sims = {p: [] for p in todo}
    for _ in range(n_outer):
        cells = {p: {"A": {}, "B": {}} for p in todo}
        for g in groups:
            pool = [u for u in units if u[1] == g]
            for u in rng.choices(pool, k=len(pool)):
                for p in todo:
                    for v, xs in units[u].get(p, {}).items():
                        cells[p][v].setdefault(g, []).extend(xs)
        for p in todo:
            es = score.effect_stats(cells[p], n_inner, rng)
            sims[p].append(score.prediction_score_distance(V[p]["prediction"], score.classify(es), es["effect"], V[p]["pair_type"])["score"])
    return sims


def summarise(sims, X, authored, tiers, n):
    means = {t: [statistics.mean(sims[p][i] for p in authored if X[p]["author_tier"] == t) for i in range(n)] for t in tiers}
    first = {t: 0 for t in tiers}
    for i in range(n):
        first[max(tiers, key=lambda t: means[t][i])] += 1
    return {"expected_score_changes_in_a_rerun_authored": round(sum(sum(abs(s - f(X[p]["prediction_score"])) > 0.25 for s in sims[p]) / n
                                                                    for p in authored), 1),
            "author_mean_sd": {t: round(statistics.pstdev(means[t]), 3) for t in tiers},
            "first": {t: round(first[t] / n, 3) for t in tiers}}


def cal_run(dirs, out, moral, moca, boot, splits, tolerate=False):
    args = [sys.executable, os.path.join(CAL, "analyse.py"), "--answers", os.path.join(CAL, "answers"), "--moral-evals", moral, "--moca", moca]
    for m in MODELS:
        args += ["--group", "%s-persona=%s" % (m, dirs[m])]
    args += ["--panel", ",".join(m + "-persona" for m in MODELS), "--boot", str(boot), "--splits", str(splits), "--out", out]
    if tolerate:
        args.append("--tolerate-empty")
    return subprocess.Popen(args, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def cal_table(d):
    ot, mt = d["otr"]["verdict_table"], d["moca"]["verdict_table"]
    conf = d["otr"]["rates"]["panel_confirmed"] + d["moca"]["rates"]["panel_confirmed"]
    hits = ot.get("hit", 0) + mt.get("hit", 0)
    return {"confirmed": conf, "hits": hits, "false_positives": ot.get("false positive", 0) + mt.get("false positive", 0),
            "share_backed_by_people": hits / conf if conf else None,
            "otr": {"confirmed": d["otr"]["rates"]["panel_confirmed"], "hits": ot.get("hit", 0), "false_positives": ot.get("false positive", 0)},
            "moca": {"confirmed": d["moca"]["rates"]["panel_confirmed"], "hits": mt.get("hit", 0), "false_positives": mt.get("false positive", 0)}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--moral-evals", required=True)
    ap.add_argument("--moca", required=True)
    ap.add_argument("--n-outer", type=int, default=300)
    ap.add_argument("--n-inner", type=int, default=400)
    ap.add_argument("--halves", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20261129)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    res = {}

    # 1. panel 1 against panel 2
    P1, P2, PP = pairs_csv("out/round2c"), pairs_csv("out/round2c_p2"), pairs_csv("out/round2c_pooled")
    ids = sorted(P1)
    authored = [p for p in ids if P1[p]["pair_type"] == "authored"]
    tiers = sorted({P1[p]["author_tier"] for p in authored})
    d2 = [(f(P1[p]["effect"]) - f(P2[p]["effect"])) ** 2 for p in ids]
    s2 = [se(P1[p]) ** 2 + se(P2[p]) ** 2 for p in ids]
    res["panel1_vs_panel2"] = {
        "n_items": len(ids), "effect_correlation": round(statistics.correlation([f(P1[p]["effect"]) for p in ids], [f(P2[p]["effect"]) for p in ids]), 3),
        "mean_abs_effect_difference": round(statistics.mean(abs(f(P1[p]["effect"]) - f(P2[p]["effect"])) for p in ids), 2),
        "noise_ratio": round(sum(d2) / sum(s2), 2),
        "verdict_changes": [p for p in ids if P1[p]["observed_direction"] != P2[p]["observed_direction"]],
        "authored_score_changes_over_0.25": [p for p in authored if abs(f(P1[p]["prediction_score"]) - f(P2[p]["prediction_score"])) > 0.25]}

    # 2. judge-level resampling, 10 against 20 ratings
    V = {p["pair_id"]: p for p in json.load(open(os.path.join(ROOT, "round2", "vignettes_c.json")))["pairs"]}
    sim1 = resample(["round2c"], V, authored, a.n_outer, a.n_inner, rng)
    simp = resample(["round2c", "round2c-p2"], V, authored, a.n_outer, a.n_inner, rng)
    res["judge_level_resampling"] = {"panel1_10_ratings": summarise(sim1, P1, authored, tiers, a.n_outer),
                                     "pooled_20_ratings": summarise(simp, PP, authored, tiers, a.n_outer)}

    # 3. authors
    res["authors"] = {t: {k: {"panel1": round(statistics.mean(f(P1[p][c]) for p in authored if P1[p]["author_tier"] == t), r),
                              "panel2": round(statistics.mean(f(P2[p][c]) for p in authored if P2[p]["author_tier"] == t), r),
                              "pooled": round(statistics.mean(f(PP[p][c]) for p in authored if PP[p]["author_tier"] == t), r)}
                          for k, c, r in (("composite", "composite", 1), ("prediction", "prediction_score", 3))} for t in tiers}
    res["controls_pooled"] = {p: {"effect": round(f(PP[p]["effect"]), 2), "groups": "%s/%s" % (PP[p]["groups_same_sign"], PP[p]["groups_total"]),
                                  "observed": PP[p]["observed_direction"] + "/" + PP[p]["observed_size"]}
                              for p in ids if PP[p]["pair_type"] in ("control_classic", "control_null")}

    # 4. the four-model persona panel on the human data: all 10 judges, and random halves
    full_dirs = {m: os.path.join(CAL, "answers_persona", m) for m in MODELS}
    for m in MODELS:
        assert len([x for x in os.listdir(full_dirs[m]) if x.endswith(".json")]) == 10, "need 10 persona answers for %s" % m
    tmp = tempfile.mkdtemp()
    full_out = os.path.join(ROOT, "reports", "calibration_numbers_persona4.json")
    jobs = [("full", cal_run(full_dirs, full_out, a.moral_evals, a.moca, 4000, 400), full_out)]
    # Deviation from the committed plan (found when it first ran, 26 November): a random 5 of a model's 10 calibration
    # judges can leave an OffTheRails scenario with no rating at one level of a factor, and the analysis then cannot
    # compute that contrast (or a condition-level mean). Halves are therefore redrawn until every scenario x factor x
    # level has at least one rating from every model, every condition of every scenario at least one rating from the
    # four models together, and every MoCa pair both of its stories from at least one model. The full panel is
    # unaffected.
    man = json.load(open(os.path.join(CAL, "manifest.json")))["batches"]

    def covered(bids):
        have = set()
        for b in bids:
            for it in man[b]["part1"]:
                c = it["condition"]
                for fk, lvl in (("cs", c.startswith("cc_")), ("ev", "_evitable_" in c), ("ac", c.endswith("action_yes"))):
                    have.add((it["scenario_id"], fk, int(lvl)))
        scen = {it["scenario_id"] for b in man for it in man[b]["part1"]}
        return all((s_, fk, l) in have for s_ in scen for fk in ("cs", "ev", "ac") for l in (0, 1))

    all_cells = {(it["scenario_id"], it["condition"]) for b in man for it in man[b]["part1"]}
    moca_pairs = [tuple(p) for p in json.load(open(os.path.join(CAL, "manifest.json")))["moca_pairs"]]
    redraws = 0
    for h in range(a.halves):
        dirs, picks = {}, {}
        while True:  # every model covers every factor level, and together they cover every condition of every scenario
            for m in MODELS:
                files = sorted(x for x in os.listdir(full_dirs[m]) if x.endswith(".json"))
                while True:
                    picks[m] = rng.sample(files, 5)
                    if covered([x[:-5] for x in picks[m]]):
                        break
                    redraws += 1
            got = {(it["scenario_id"], it["condition"]) for m in MODELS for x in picks[m] for it in man[x[:-5]]["part1"]}
            seen = {m: {sid for x in picks[m] for sid in man[x[:-5]]["part2"]} for m in MODELS}
            moca_ok = all(any(a_ in seen[m] and b_ in seen[m] for m in MODELS) for a_, b_ in moca_pairs)
            if got >= all_cells and moca_ok:
                break
            redraws += 1
        for m in MODELS:
            pick = picks[m]
            d = os.path.join(tmp, "h%02d_%s" % (h, m))
            os.makedirs(d)
            for x in pick:
                shutil.copy(os.path.join(full_dirs[m], x), d)
            dirs[m] = d
        jobs.append(("half", None, (dirs, os.path.join(tmp, "h%02d.json" % h))))
    out_full, halves = None, []
    running = [jobs[0]]
    queue = jobs[1:]
    full_same_settings = os.path.join(tmp, "full_1000.json")
    queue.append(("full_same", None, (full_dirs, full_same_settings)))
    while running or queue:
        while queue and len(running) < 4:
            kind, _, (dirs, out) = queue.pop(0)
            running.append((kind, cal_run(dirs, out, a.moral_evals, a.moca, 1000, 20, tolerate=(kind == "half")), out))
        kind, p, out = running.pop(0)
        _, err = p.communicate()
        if p.returncode != 0:
            raise SystemExit("calibration run failed: " + err[-2000:])
        t = cal_table(json.load(open(out)))
        if kind == "full":
            out_full = t
        elif kind == "full_same":
            res_full_same = t
        else:
            halves.append(t)
    shutil.rmtree(tmp)
    res["calibration_persona4"] = {
        "all_10_judges_per_model": out_full,
        "all_10_judges_per_model_same_settings_as_halves": res_full_same,
        "halves_5_judges_per_model": {"n": len(halves),
                                      "mean_confirmed": round(statistics.mean(h["confirmed"] for h in halves), 1),
                                      "mean_hits": round(statistics.mean(h["hits"] for h in halves), 1),
                                      "mean_false_positives": round(statistics.mean(h["false_positives"] for h in halves), 1),
                                      "mean_share_backed_by_people": round(statistics.mean(h["share_backed_by_people"] for h in halves if h["share_backed_by_people"] is not None), 3)},
        "halves_redrawn_for_coverage": redraws,
        "earlier_panels_for_comparison": "persona x3 under two-thirds: 33 confirmed, 13 backed, 39%; plain x4: 38, 12, 32%"}

    # criteria
    e1 = res["judge_level_resampling"]["panel1_10_ratings"]["expected_score_changes_in_a_rerun_authored"]
    ep = res["judge_level_resampling"]["pooled_20_ratings"]["expected_score_changes_in_a_rerun_authored"]
    c1 = ep <= 0.5 * e1
    s10 = res_full_same["share_backed_by_people"]
    s5 = res["calibration_persona4"]["halves_5_judges_per_model"]["mean_share_backed_by_people"]
    c2 = s10 is not None and s10 >= s5 - 0.05
    res["criteria"] = {"C1_stability": {"pass": c1, "expected_changes_10": e1, "expected_changes_20": ep, "needs": "20 <= half of 10"},
                       "C2_no_validity_cost": {"pass": c2, "share_10_judges": round(s10, 3) if s10 is not None else None, "mean_share_5_judges": s5,
                                               "needs": "share with 10 >= mean share with 5 - 0.05"},
                       "adopt_20_ratings": c1 and c2}
    out = os.path.join(ROOT, "reports", "round2c_panels_numbers.json")
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res["panel1_vs_panel2"]))
    print(json.dumps(res["judge_level_resampling"]))
    for t, x in res["authors"].items():
        print(t, json.dumps(x))
    for p, c in res["controls_pooled"].items():
        print("  control %-24s %+.2f %s %s" % (p, c["effect"], c["groups"], c["observed"]))
    print("calibration, four-model persona panel:", json.dumps(res["calibration_persona4"]))
    print("criteria:", json.dumps(res["criteria"]))
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
