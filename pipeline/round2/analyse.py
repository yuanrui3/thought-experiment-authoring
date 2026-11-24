#!/usr/bin/env python3
"""Round 2: what the three contested factors show.

    python3 pipeline/round2/analyse.py

Reads out/round2, out/persona, out/pair_scores.csv, judgments.csv and round2/vignettes.json (run score.py for round 2
first) and writes reports/round2_numbers.json. Four questions:

  1. Do the new factors separate the authors more than the three the pilot found too easy?
  2. Do the three new classic controls show the gap people showed?
  3. Test-retest: the 15 pairs reused from the pilot were judged twice by the same kind of panel (pilot persona run,
     round 2). How often does the verdict, or the author's score, change?
  4. Fragility: if the round-2 panel were run again with judges like these, how often would each authored pair keep
     its score? Simulated by resampling the ratings inside each judge-model x version cell and applying the scoring
     rule to every resample. This understates rerun noise (it keeps the same personas and the same batch context);
     question 3 measures the real thing on the reused pairs.
"""
import csv, json, os, random, statistics, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
import score  # noqa: E402

OUT = os.path.join(ROOT, "reports", "round2_numbers.json")
EASY = ["intent_accident", "knowledge_luck", "moral_luck"]
NEW = ["inevitable_harm", "knowledge_causation", "luck_wrongness"]
KEPT = ["doing_allowing", "norm_causation"]


def pairs_csv(path):
    return {r["pair_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def f(x):
    return float(x)


def main(n_outer=300, n_inner=400, seed=20261122):
    r2 = pairs_csv(os.path.join(ROOT, "out", "round2", "pair_scores.csv"))
    pp = pairs_csv(os.path.join(ROOT, "out", "persona", "pair_scores.csv"))
    pm = pairs_csv(os.path.join(ROOT, "out", "pair_scores.csv"))
    V = {p["pair_id"]: p for p in json.load(open(os.path.join(ROOT, "round2", "vignettes.json")))["pairs"]}
    res = {}

    # 1. factor difficulty and spread
    def factor_table(rows, factors):
        t = {}
        for fac in factors:
            rr = [r for r in rows.values() if r["pair_type"] == "authored" and r["factor_id"] == fac]
            ps = [f(r["prediction_score"]) for r in rr]
            t[fac] = {"n_authors": len(rr), "mean_prediction_score": round(statistics.mean(ps), 3),
                      "sd_prediction_score": round(statistics.pstdev(ps), 3),
                      "share_full_marks": round(sum(1 for x in ps if x >= 0.999) / len(ps), 3),
                      "mean_abs_effect": round(statistics.mean(abs(f(r["effect"])) for r in rr), 2),
                      "by_author": {r["author_tier"]: {"prediction_score": round(f(r["prediction_score"]), 2),
                                                       "effect": round(f(r["effect"]), 2),
                                                       "observed": r["observed_direction"] + "/" + r["observed_size"]}
                                    for r in rr}}
        return t
    res["factors"] = {"pilot_main_panel_easy": factor_table(pm, EASY), "pilot_persona_panel_easy": factor_table(pp, EASY),
                      "pilot_persona_panel_kept": factor_table(pp, KEPT),
                      "round2_new": factor_table(r2, NEW), "round2_kept": factor_table(r2, KEPT)}
    # same three authors only, for a like-for-like comparison of the easy and new factors
    def three(rows, factors):
        ps = [f(r["prediction_score"]) for r in rows.values() if r["pair_type"] == "authored"
              and r["factor_id"] in factors and r["author_tier"] in ("haiku", "sonnet", "opus")]
        return {"n_pairs": len(ps), "mean_prediction_score": round(statistics.mean(ps), 3),
                "share_full_marks": round(sum(1 for x in ps if x >= 0.999) / len(ps), 3),
                "share_zero": round(sum(1 for x in ps if x == 0) / len(ps), 3)}
    res["three_authors"] = {"easy_factors_pilot_persona_panel": three(pp, EASY), "easy_factors_pilot_main_panel": three(pm, EASY),
                            "new_factors_round2": three(r2, NEW)}
    res["authors_new_factors"] = {}
    for t in ("haiku", "sonnet", "opus"):
        rr = [r2["r2_%s_%s" % (t, fac)] for fac in NEW]
        res["authors_new_factors"][t] = {"mean_prediction_score": round(statistics.mean(f(r["prediction_score"]) for r in rr), 3),
                                         "mean_composite": round(statistics.mean(f(r["composite"]) for r in rr), 1),
                                         "demonstrated": sum(1 for r in rr if r["gap_demonstrated"] == "True"),
                                         "mean_confound_severity": round(statistics.mean(f(r["confound_severity"]) for r in rr), 2),
                                         "mean_originality": round(statistics.mean(f(r["originality"]) for r in rr), 2)}

    # 2. new classic controls against people
    res["controls"] = {}
    for pid in ("cc_inevitable_harm", "cc_knowledge_causation", "cc_luck_wrongness"):
        r = r2[pid]
        res["controls"][pid] = {"panel_mean_a": round(f(r["mean_a"]), 2), "panel_mean_b": round(f(r["mean_b"]), 2),
                                "panel_effect": round(f(r["effect"]), 2), "ci": [round(f(r["ci_low"]), 2), round(f(r["ci_high"]), 2)],
                                "groups_same_sign": int(r["groups_same_sign"]), "observed": r["observed_direction"] + "/" + r["observed_size"],
                                "reproduced": r["gap_demonstrated"] == "True",
                                "human_result": V[pid]["reference"]["human_result"] if "reference" in V[pid] else None}

    # 3. test-retest on the reused pairs
    shared = [p for p in r2 if p in pp]
    rows = []
    for p in shared:
        a, b = pp[p], r2[p]
        rows.append({"pair_id": p, "pair_type": b["pair_type"], "pilot_persona_effect": round(f(a["effect"]), 2),
                     "round2_effect": round(f(b["effect"]), 2),
                     "pilot_persona_verdict": a["observed_direction"], "round2_verdict": b["observed_direction"],
                     "pilot_persona_score": round(f(a["prediction_score"]), 2), "round2_score": round(f(b["prediction_score"]), 2)})
    xs, ys = [r["pilot_persona_effect"] for r in rows], [r["round2_effect"] for r in rows]
    res["test_retest"] = {
        "n_pairs": len(rows), "rows": rows,
        "effect_correlation": round(statistics.correlation(xs, ys), 3),
        "mean_abs_effect_difference": round(statistics.mean(abs(x - y) for x, y in zip(xs, ys)), 2),
        "max_abs_effect_difference": round(max(abs(x - y) for x, y in zip(xs, ys)), 2),
        "verdict_changes": [r["pair_id"] for r in rows if r["pilot_persona_verdict"] != r["round2_verdict"]],
        "authored_score_changes": [r["pair_id"] for r in rows if r["pair_type"] == "authored"
                                   and abs(r["pilot_persona_score"] - r["round2_score"]) > 0.25],
        "n_authored": sum(1 for r in rows if r["pair_type"] == "authored"),
    }

    # 4. fragility of each authored and classic pair in round 2
    J = score.load_judgments(os.path.join(ROOT, "judgments.csv"), "round2")
    cells = {}
    for r in J:
        cells.setdefault(r["pair_id"], {"A": {}, "B": {}})[r["version"]].setdefault(r["judge_group"], []).append(r["rating"])
    rng = random.Random(seed)
    todo = [pid for pid, p in V.items() if p["pair_type"] in ("authored", "control_classic") and pid in r2]
    scores = {pid: [] for pid in todo}
    demo = {pid: 0 for pid in todo}
    for _ in range(n_outer):
        for pid in todo:
            p = V[pid]
            pred = p["prediction"] if "prediction" in p else {"direction": p["predicted_direction"], "size": p["predicted_size"]}
            c = {v: {g: rng.choices(xs, k=len(xs)) for g, xs in cells[pid][v].items()} for v in "AB"}
            es = score.effect_stats(c, n_inner, rng)
            obs = score.classify(es)
            s = score.prediction_score_distance(pred, obs, es["effect"], p["pair_type"])
            scores[pid].append(s["score"])
            demo[pid] += s["demonstrated"]
    frag = {}
    for pid in todo:
        observed = f(r2[pid]["prediction_score"])
        frag[pid] = {"observed_score": round(observed, 2), "mean_resampled_score": round(statistics.mean(scores[pid]), 2),
                     "share_within_0.25_of_observed": round(sum(1 for s in scores[pid] if abs(s - observed) <= 0.25) / n_outer, 2),
                     "share_demonstrated": round(demo[pid] / n_outer, 2)}
    # author order on the new factors across the same reruns (composite moves with the prediction score at weight 0.40;
    # no round-2 pair is format-capped, checked below)
    assert not any("format" in r2[pid]["flags"] for pid in todo), "a format-capped pair: the linear composite shortcut does not hold"
    tiers = ("haiku", "sonnet", "opus")
    orders = {}
    for i in range(n_outer):
        m = {t: statistics.mean(scores["r2_%s_%s" % (t, fac)][i] for fac in NEW) for t in tiers}
        key = " > ".join(sorted(tiers, key=lambda t: -m[t]))
        orders[key] = orders.get(key, 0) + 1
    res["fragility"] = {"method": "resample ratings inside each judge-model x version cell (%d reruns, %d-draw bootstrap "
                                  "interval inside each), then apply the scoring rule" % (n_outer, n_inner), "pairs": frag,
                        "author_order_new_factors_by_mean_prediction_score": {k: round(v / n_outer, 3) for k, v in
                                                                               sorted(orders.items(), key=lambda kv: -kv[1])},
                        # added 22 Nov for comparison with round 2b (no extra random draws, so the numbers above are unchanged)
                        "author_mean_sd_across_reruns": {t: round(statistics.pstdev(
                            statistics.mean(scores["r2_%s_%s" % (t, fac)][i] for fac in NEW) for i in range(n_outer)), 3)
                            for t in tiers}}
    json.dump(res, open(OUT, "w"), indent=1)

    # printout
    print("factor difficulty (authored pairs; prediction score under the current rule)")
    for k, t in res["factors"].items():
        for fac, x in t.items():
            print("  %-28s %-20s mean %.2f  sd %.2f  full %.2f  |effect| %.2f" % (k, fac, x["mean_prediction_score"], x["sd_prediction_score"],
                                                                                 x["share_full_marks"], x["mean_abs_effect"]))
    print("same three authors:", json.dumps(res["three_authors"]))
    print("authors on new factors:", json.dumps(res["authors_new_factors"]))
    for k, x in res["controls"].items():
        print("control %-24s %.2f vs %.2f  effect %+.2f  %s  reproduced %s" % (k, x["panel_mean_a"], x["panel_mean_b"], x["panel_effect"], x["observed"], x["reproduced"]))
    tr = res["test_retest"]
    print("test-retest: r = %.3f, mean |diff| %.2f, max %.2f; verdict changes %s; authored score changes %s of %d" % (
        tr["effect_correlation"], tr["mean_abs_effect_difference"], tr["max_abs_effect_difference"], tr["verdict_changes"],
        tr["authored_score_changes"], tr["n_authored"]))
    for pid, x in frag.items():
        print("  fragility %-30s observed %.2f  resampled mean %.2f  kept %.2f  demonstrated %.2f" % (
            pid, x["observed_score"], x["mean_resampled_score"], x["share_within_0.25_of_observed"], x["share_demonstrated"]))
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    # --agreement-rule three_quarters rebuilds the numbers as first published (rescore the out/ folders the same way first)
    if "--agreement-rule" in sys.argv:
        score.set_agreement_rule(sys.argv[sys.argv.index("--agreement-rule") + 1])
    main()
