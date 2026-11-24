#!/usr/bin/env python3
"""Round 2b, two independent panels on the same pairs: how big is the panel-to-panel error, and what survives it?

    python3 pipeline/round2/analyse_panels.py

Score the panels first (same pairs, same audits):
    python3 score.py --vignettes round2/vignettes_b.json --run round2b            --audit-run main,round2,round2b --out out/round2b        --no-report
    python3 score.py --vignettes round2/vignettes_b.json --run round2b-p2         --audit-run main,round2,round2b --out out/round2b_p2     --no-report
    python3 score.py --vignettes round2/vignettes_b.json --run round2b,round2b-p2 --audit-run main,round2,round2b --out out/round2b_pooled --no-report

Writes reports/round2b_panels_numbers.json.

  1. Panel 1 against panel 2, pair by pair: gaps, verdicts, scores.
  2. Is the difference between panels larger than each panel's own sampling error? For every pair, the squared
     difference of the two gaps is compared with the sum of the two squared standard errors (taken from each panel's
     95% interval). A ratio near 1 means the panels differ only by sampling noise; well above 1 means each run carries
     a shift of its own. The same test on round 2 against panel 1 (the nine round-2 pairs and ten controls, judged in
     a different batch mix) shows whether batch context adds to it.
  3. Authors in each panel and pooled; the panel-to-panel difference of each author's mean.
  4. Judge-level resampling: whole judges (one repeat = the x and y judge of one model, which together cover both
     versions of every pair) are resampled within each model, and every pair is rescored. Unlike resampling single
     ratings, this keeps a judge's habits across pairs. Done for panel 1 alone (to compare with its actual difference
     from panel 2) and for the pooled panels (author order and its stability).
  5. A permutation test of the author differences on the pooled scores, shuffling authors within each factor.
"""
import csv, itertools, json, math, os, random, statistics, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
import score  # noqa: E402

OUT = os.path.join(ROOT, "reports", "round2b_panels_numbers.json")
NEW = ["inevitable_harm", "knowledge_causation", "luck_wrongness"]
TIERS = ["haiku", "sonnet", "opus"]
RUN1, RUN2 = "round2b", "round2b-p2"


def pairs_csv(path):
    return {r["pair_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def f(x):
    return float(x)


def se(r):
    return (f(r["ci_high"]) - f(r["ci_low"])) / (2 * 1.96)


def order_key(m):
    return " > ".join(sorted(m, key=lambda t: -m[t]))


def compare(a, b, ids):
    """Two scorings of the same pairs: agreement of gaps, verdicts and scores, and the noise ratio."""
    d2 = [(f(a[p]["effect"]) - f(b[p]["effect"])) ** 2 for p in ids]
    s2 = [se(a[p]) ** 2 + se(b[p]) ** 2 for p in ids]
    xs, ys = [f(a[p]["effect"]) for p in ids], [f(b[p]["effect"]) for p in ids]
    scored = [p for p in ids if a[p]["pair_type"] != "control_null"]
    return {"n_pairs": len(ids), "effect_correlation": round(statistics.correlation(xs, ys), 3),
            "mean_abs_effect_difference": round(statistics.mean(abs(x - y) for x, y in zip(xs, ys)), 2),
            "noise_ratio": round(sum(d2) / sum(s2), 2),
            "noise_ratio_note": "sum of squared gap differences / sum of (SE1^2 + SE2^2); about 1 if the runs differ by sampling noise only",
            "verdict_changes": [p for p in ids if a[p]["observed_direction"] != b[p]["observed_direction"]],
            "score_changes_over_0.25": [p for p in scored if abs(f(a[p]["prediction_score"]) - f(b[p]["prediction_score"])) > 0.25],
            "n_scored": len(scored)}


def main(n_outer=300, n_inner=400, n_perm=20000, seed=20261124):
    P1 = pairs_csv(os.path.join(ROOT, "out", "round2b", "pair_scores.csv"))
    P2 = pairs_csv(os.path.join(ROOT, "out", "round2b_p2", "pair_scores.csv"))
    PO = pairs_csv(os.path.join(ROOT, "out", "round2b_pooled", "pair_scores.csv"))
    R2 = pairs_csv(os.path.join(ROOT, "out", "round2", "pair_scores.csv"))
    V = {p["pair_id"]: p for p in json.load(open(os.path.join(ROOT, "round2", "vignettes_b.json")))["pairs"]}
    authored = [p for p in P1 if P1[p]["pair_type"] == "authored"]
    res = {}

    # 1-2. panel against panel, and round 2 against panel 1
    ids = list(P1)
    res["panel1_vs_panel2"] = compare(P1, P2, ids)
    res["panel1_vs_panel2_authored_only"] = compare(P1, P2, authored)
    shared = [p for p in P1 if p in R2]
    res["round2_vs_panel1"] = compare(R2, P1, shared)
    res["round2_vs_panel2"] = compare(R2, P2, shared)
    res["pairs"] = {p: {"type": P1[p]["pair_type"],
                        "effect": [round(f(X[p]["effect"]), 2) for X in (P1, P2, PO)],
                        "verdict": [X[p]["observed_direction"] for X in (P1, P2, PO)],
                        "groups_same_sign": [int(X[p]["groups_same_sign"]) for X in (P1, P2, PO)],
                        "score": [round(f(X[p]["prediction_score"]), 2) for X in (P1, P2, PO)],
                        "round2": None if p not in R2 else {"effect": round(f(R2[p]["effect"]), 2),
                                                            "verdict": R2[p]["observed_direction"],
                                                            "score": round(f(R2[p]["prediction_score"]), 2)}}
                    for p in ids}
    res["pairs_note"] = "lists are [panel 1, panel 2, pooled]"
    res["common_shift"] = {name: {"mean_score_authored": round(statistics.mean(f(X[p]["prediction_score"]) for p in authored), 3),
                                  "mean_abs_effect_authored": round(statistics.mean(abs(f(X[p]["effect"])) for p in authored), 2),
                                  "authored_all_models_agree": sum(X[p]["groups_same_sign"] == "3" for p in authored),
                                  "authored_demonstrated": sum(X[p]["gap_demonstrated"] == "True" for p in authored)}
                           for name, X in (("panel1", P1), ("panel2", P2), ("pooled", PO))}

    # 3. authors
    def authors(X):
        out = {}
        for t in TIERS:
            mine = [p for p in authored if X[p]["author_tier"] == t]
            out[t] = {"mean_prediction_score": round(statistics.mean(f(X[p]["prediction_score"]) for p in mine), 3),
                      "mean_composite": round(statistics.mean(f(X[p]["composite"]) for p in mine), 1),
                      "demonstrated": sum(X[p]["gap_demonstrated"] == "True" for p in mine),
                      "full_marks": sum(f(X[p]["prediction_score"]) >= 0.999 for p in mine),
                      "by_factor": {fac: round(statistics.mean(f(X[p]["prediction_score"]) for p in mine if X[p]["factor_id"] == fac), 3)
                                    for fac in NEW}}
        return out
    res["authors"] = {"panel1": authors(P1), "panel2": authors(P2), "pooled": authors(PO)}
    res["author_order"] = {k: order_key({t: v[t]["mean_prediction_score"] for t in TIERS}) for k, v in res["authors"].items()}
    res["author_panel_difference"] = {t: round(res["authors"]["panel2"][t]["mean_prediction_score"]
                                               - res["authors"]["panel1"][t]["mean_prediction_score"], 3) for t in TIERS}

    # 4. judge-level resampling
    rows = score.load_judgments(os.path.join(ROOT, "judgments.csv"), RUN1 + "," + RUN2)
    units = {}  # (run, model, repeat) -> {pair: {version: [ratings]}}
    for r in rows:
        u = (r["run_id"], r["judge_group"], r["repeat"])
        units.setdefault(u, {}).setdefault(r["pair_id"], {}).setdefault(r["version"], []).append(r["rating"])
    todo = [p for p in V if V[p]["pair_type"] in ("authored", "control_classic")]
    rng = random.Random(seed)

    def resample(runs, n):
        groups = sorted({u[1] for u in units})
        sims = {p: [] for p in todo}
        for _ in range(n):
            cells = {p: {"A": {}, "B": {}} for p in todo}
            for g in groups:
                pool = [u for u in units if u[1] == g and u[0] in runs]
                for u in rng.choices(pool, k=len(pool)):
                    for p in todo:
                        for v, xs in units[u].get(p, {}).items():
                            cells[p][v].setdefault(g, []).extend(xs)
            for p in todo:
                es = score.effect_stats(cells[p], n_inner, rng)
                s = score.prediction_score_distance(V[p]["prediction"], score.classify(es), es["effect"], V[p]["pair_type"])
                sims[p].append(s["score"])
        return sims

    def summarise(sims, X, n):
        means = {t: [statistics.mean(sims[p][i] for p in authored if X[p]["author_tier"] == t) for i in range(n)] for t in TIERS}
        orders = {}
        for i in range(n):
            k = order_key({t: means[t][i] for t in TIERS})
            orders[k] = orders.get(k, 0) + 1
        return {"author_mean_sd": {t: round(statistics.pstdev(means[t]), 3) for t in TIERS},
                "author_order": {k: round(v / n, 3) for k, v in sorted(orders.items(), key=lambda kv: -kv[1])},
                "first": {t: round(sum(1 for k, v in orders.items() for _ in range(v) if k.startswith(t)) / n, 3) for t in TIERS},
                "last": {t: round(sum(v for k, v in orders.items() if k.endswith(t)) / n, 3) for t in TIERS},
                "authored_pairs_kept_below_0.8": sum(1 for p in authored
                                                     if sum(abs(s - f(X[p]["prediction_score"])) <= 0.25 for s in sims[p]) / n < 0.8),
                "expected_score_changes_in_a_rerun_authored": round(sum(
                    sum(abs(s - f(X[p]["prediction_score"])) > 0.25 for s in sims[p]) / n for p in authored), 1)}
    sim1 = resample({RUN1}, n_outer)
    simp = resample({RUN1, RUN2}, n_outer)
    res["judge_level_resampling"] = {
        "method": "repeats (an x and a y judge of one model) resampled with replacement within each model; %d resamples, "
                  "%d-draw interval inside each" % (n_outer, n_inner),
        "panel1": summarise(sim1, P1, n_outer),
        "pooled": summarise(simp, PO, n_outer)}
    res["judge_level_resampling"]["panel1"]["actual_score_changes_in_panel2_authored"] = len(
        res["panel1_vs_panel2_authored_only"]["score_changes_over_0.25"])

    # 5. permutation test on pooled scores
    ps = {p: f(PO[p]["prediction_score"]) for p in authored}
    tier = {p: PO[p]["author_tier"] for p in authored}
    fac = {p: PO[p]["factor_id"] for p in authored}
    def perm(a, c):
        ids2 = [p for p in authored if tier[p] in (a, c)]
        obs = statistics.mean(ps[p] for p in ids2 if tier[p] == a) - statistics.mean(ps[p] for p in ids2 if tier[p] == c)
        h = 0
        for _ in range(n_perm):
            lab = {}
            for fc in NEW:
                fid = [p for p in ids2 if fac[p] == fc]
                tt = [tier[p] for p in fid]
                rng.shuffle(tt)
                lab.update(zip(fid, tt))
            d = statistics.mean(ps[p] for p in ids2 if lab[p] == a) - statistics.mean(ps[p] for p in ids2 if lab[p] == c)
            h += abs(d) >= abs(obs) - 1e-12
        return {"difference": round(obs, 3), "permutation_p": round((h + 1) / (n_perm + 1), 4)}
    res["pooled_pairwise_permutation"] = {"%s - %s" % (a, c): perm(a, c) for a, c in itertools.combinations(TIERS, 2)}
    res["controls"] = {p: {"effect": res["pairs"][p]["effect"], "verdict": res["pairs"][p]["verdict"]}
                       for p in ids if P1[p]["pair_type"] != "authored"}
    json.dump(res, open(OUT, "w"), indent=1)

    for k in ("panel1_vs_panel2", "panel1_vs_panel2_authored_only", "round2_vs_panel1", "round2_vs_panel2"):
        x = res[k]
        print("%-32s n %2d  r %.3f  mean|diff| %.2f  noise ratio %.2f  verdict changes %d  score changes %d/%d" % (
            k, x["n_pairs"], x["effect_correlation"], x["mean_abs_effect_difference"], x["noise_ratio"],
            len(x["verdict_changes"]), len(x["score_changes_over_0.25"]), x["n_scored"]))
        print("      verdicts:", x["verdict_changes"], "| scores:", x["score_changes_over_0.25"])
    print("common shift:", json.dumps(res["common_shift"]))
    for k, v in res["authors"].items():
        print("authors %-7s" % k, "  ".join("%s %.2f/%.1f (%s)" % (t, v[t]["mean_prediction_score"], v[t]["mean_composite"],
                                                                  " ".join("%.2f" % v[t]["by_factor"][fc] for fc in NEW)) for t in TIERS),
              "|", res["author_order"][k])
    print("author panel difference (p2 - p1):", res["author_panel_difference"])
    for k in ("panel1", "pooled"):
        print("judge-level", k, json.dumps(res["judge_level_resampling"][k]))
    print("pooled permutation:", json.dumps(res["pooled_pairwise_permutation"]))
    for p, c in res["controls"].items():
        print("  control %-24s %s %s" % (p, c["effect"], c["verdict"]))
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    # --agreement-rule three_quarters rebuilds the numbers as first published (rescore the out/ folders the same way first)
    if "--agreement-rule" in sys.argv:
        score.set_agreement_rule(sys.argv[sys.argv.index("--agreement-rule") + 1])
    main()
