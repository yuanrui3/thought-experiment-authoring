#!/usr/bin/env python3
"""Round 2c: all four authors, nine pairs each on the three new factors, judged in one run by four judge models.

    python3 pipeline/round2/analyse_c.py

Score the round first:
    python3 score.py --vignettes round2/vignettes_c.json --run round2c --audit-run main,round2,round2b,round2c --out out/round2c --no-report

Reads out/round2c, out/round2b_pooled, judgments.csv and round2/vignettes_c.json; writes reports/round2c_numbers.json.
The shared-pool prediction score is computed separately by pipeline/shared_pool.py (reports/shared_pool_round2c_numbers.json).

  1. Authors: composite and prediction score over their nine pairs, by factor, audits.
  2. Judge-level resampling within the run: the spread of each author's mean and how often each order occurs.
  3. A permutation test of author differences, shuffling authors among the twelve pairs of each factor.
  4. The 27 earlier pairs and the 10 controls against the pooled round-2b panels: a different panel (four judge models
     instead of three, 46-item batches instead of 37), so this is a replication across panels, not a test-retest.
"""
import csv, itertools, json, os, random, statistics, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
import score  # noqa: E402

OUT = os.path.join(ROOT, "reports", "round2c_numbers.json")
NEW = ["inevitable_harm", "knowledge_causation", "luck_wrongness"]
RUN = "round2c"


def pairs_csv(path):
    return {r["pair_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def f(x):
    return float(x)


def se(r):
    return (f(r["ci_high"]) - f(r["ci_low"])) / (2 * 1.96)


def main(n_outer=300, n_inner=400, n_perm=20000, seed=20261126):
    C = pairs_csv(os.path.join(ROOT, "out", "round2c", "pair_scores.csv"))
    B = pairs_csv(os.path.join(ROOT, "out", "round2b_pooled", "pair_scores.csv"))
    V = {p["pair_id"]: p for p in json.load(open(os.path.join(ROOT, "round2", "vignettes_c.json")))["pairs"]}
    authored = [p for p in C if C[p]["pair_type"] == "authored"]
    tiers = sorted({C[p]["author_tier"] for p in authored})
    res = {"run": RUN, "authors": {}}

    for t in tiers:
        mine = [p for p in authored if C[p]["author_tier"] == t]
        res["authors"][t] = {
            "n_pairs": len(mine),
            "mean_prediction_score": round(statistics.mean(f(C[p]["prediction_score"]) for p in mine), 3),
            "mean_composite": round(statistics.mean(f(C[p]["composite"]) for p in mine), 1),
            "demonstrated": sum(C[p]["gap_demonstrated"] == "True" for p in mine),
            "full_marks": sum(f(C[p]["prediction_score"]) >= 0.999 for p in mine),
            "mean_confound_severity": round(statistics.mean(f(C[p]["confound_severity"]) for p in mine), 2),
            "mean_originality": round(statistics.mean(f(C[p]["originality"]) for p in mine), 2),
            "by_factor": {fac: round(statistics.mean(f(C[p]["prediction_score"]) for p in mine if C[p]["factor_id"] == fac), 3) for fac in NEW},
            "pairs": {p: {"title": C[p]["title"], "predicted": C[p]["predicted_direction"] + "/" + C[p]["predicted_size"],
                          "effect": round(f(C[p]["effect"]), 2), "groups": "%s/%s" % (C[p]["groups_same_sign"], C[p]["groups_total"]),
                          "observed": C[p]["observed_direction"] + "/" + C[p]["observed_size"],
                          "prediction_score": round(f(C[p]["prediction_score"]), 2), "composite": round(f(C[p]["composite"]), 1),
                          "confound_severity": C[p]["confound_severity"], "originality": C[p]["originality"]} for p in sorted(mine)}}
    res["order_by_composite"] = " > ".join(sorted(tiers, key=lambda t: -res["authors"][t]["mean_composite"]))
    res["order_by_prediction_score"] = " > ".join(sorted(tiers, key=lambda t: -res["authors"][t]["mean_prediction_score"]))

    # judge-level resampling within the run
    rows = score.load_judgments(os.path.join(ROOT, "judgments.csv"), RUN)
    units = {}
    for r in rows:
        units.setdefault((r["judge_group"], r["repeat"]), {}).setdefault(r["pair_id"], {}).setdefault(r["version"], []).append(r["rating"])
    groups = sorted({u[0] for u in units})
    rng = random.Random(seed)
    todo = [p for p in V if V[p]["pair_type"] in ("authored", "control_classic")]
    sims = {p: [] for p in todo}
    for _ in range(n_outer):
        cells = {p: {"A": {}, "B": {}} for p in todo}
        for g in groups:
            pool = [u for u in units if u[0] == g]
            for u in rng.choices(pool, k=len(pool)):
                for p in todo:
                    for v, xs in units[u].get(p, {}).items():
                        cells[p][v].setdefault(g, []).extend(xs)
        for p in todo:
            es = score.effect_stats(cells[p], n_inner, rng)
            sims[p].append(score.prediction_score_distance(V[p]["prediction"], score.classify(es), es["effect"], V[p]["pair_type"])["score"])
    means = {t: [statistics.mean(sims[p][i] for p in authored if C[p]["author_tier"] == t) for i in range(n_outer)] for t in tiers}
    orders = {}
    for i in range(n_outer):
        k = " > ".join(sorted(tiers, key=lambda t: -means[t][i]))
        orders[k] = orders.get(k, 0) + 1
    res["judge_level_resampling"] = {
        "n": n_outer, "author_mean_sd": {t: round(statistics.pstdev(means[t]), 3) for t in tiers},
        "order_by_prediction_score": {k: round(v / n_outer, 3) for k, v in sorted(orders.items(), key=lambda kv: -kv[1])[:8]},
        "first": {t: round(sum(v for k, v in orders.items() if k.startswith(t)) / n_outer, 3) for t in tiers},
        "last": {t: round(sum(v for k, v in orders.items() if k.endswith(t)) / n_outer, 3) for t in tiers},
        "authored_pairs_kept_below_0.8": sum(1 for p in authored
                                             if sum(abs(s - f(C[p]["prediction_score"])) <= 0.25 for s in sims[p]) / n_outer < 0.8)}

    # permutation test, authors shuffled within factor
    ps = {p: f(C[p]["prediction_score"]) for p in authored}
    tier = {p: C[p]["author_tier"] for p in authored}
    perm = {}
    for a, b in itertools.combinations(tiers, 2):
        ids = [p for p in authored if tier[p] in (a, b)]
        obs = statistics.mean(ps[p] for p in ids if tier[p] == a) - statistics.mean(ps[p] for p in ids if tier[p] == b)
        h = 0
        for _ in range(n_perm):
            lab = {}
            for fac in NEW:
                fid = [p for p in ids if C[p]["factor_id"] == fac]
                tt = [tier[p] for p in fid]
                rng.shuffle(tt)
                lab.update(zip(fid, tt))
            d = statistics.mean(ps[p] for p in ids if lab[p] == a) - statistics.mean(ps[p] for p in ids if lab[p] == b)
            h += abs(d) >= abs(obs) - 1e-12
        perm["%s - %s" % (a, b)] = {"difference": round(obs, 3), "permutation_p": round((h + 1) / (n_perm + 1), 4)}
    res["pairwise_permutation"] = perm

    # replication of the 37 round-2b items
    shared = [p for p in C if p in B]
    d2 = [(f(C[p]["effect"]) - f(B[p]["effect"])) ** 2 for p in shared]
    s2 = [se(C[p]) ** 2 + se(B[p]) ** 2 for p in shared]
    xs, ys = [f(B[p]["effect"]) for p in shared], [f(C[p]["effect"]) for p in shared]
    scored = [p for p in shared if C[p]["pair_type"] != "control_null"]
    res["replication_vs_round2b_pooled"] = {
        "n_items": len(shared), "effect_correlation": round(statistics.correlation(xs, ys), 3),
        "mean_abs_effect_difference": round(statistics.mean(abs(x - y) for x, y in zip(xs, ys)), 2),
        "noise_ratio": round(sum(d2) / sum(s2), 2),
        "verdict_changes": [p for p in shared if C[p]["observed_direction"] != B[p]["observed_direction"]],
        "score_changes_over_0.25": [p for p in scored if abs(f(C[p]["prediction_score"]) - f(B[p]["prediction_score"])) > 0.25],
        "authors_on_shared_pairs": {t: {"round2b_pooled": round(statistics.mean(f(B[p]["prediction_score"]) for p in shared if C[p]["pair_type"] == "authored" and C[p]["author_tier"] == t), 3),
                                        "round2c": round(statistics.mean(f(C[p]["prediction_score"]) for p in shared if C[p]["pair_type"] == "authored" and C[p]["author_tier"] == t), 3)}
                                    for t in tiers if t != "fable"}}
    res["controls"] = {p: {"effect": round(f(C[p]["effect"]), 2), "groups": "%s/%s" % (C[p]["groups_same_sign"], C[p]["groups_total"]),
                           "observed": C[p]["observed_direction"] + "/" + C[p]["observed_size"]}
                       for p in C if C[p]["pair_type"] in ("control_classic", "control_null")}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)

    for t in tiers:
        a = res["authors"][t]
        print("%-7s prediction %.2f  composite %.1f  demonstrated %d/9  full %d  confound %.2f  originality %.2f  by factor %s" % (
            t, a["mean_prediction_score"], a["mean_composite"], a["demonstrated"], a["full_marks"], a["mean_confound_severity"],
            a["mean_originality"], a["by_factor"]))
    print("order by composite:", res["order_by_composite"], "| by prediction:", res["order_by_prediction_score"])
    print("judge-level:", json.dumps(res["judge_level_resampling"]))
    print("permutation:", json.dumps(perm))
    print("replication vs round 2b pooled:", json.dumps(res["replication_vs_round2b_pooled"]))
    for p, c in res["controls"].items():
        print("  control %-24s %+.2f %s %s" % (p, c["effect"], c["groups"], c["observed"]))
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    if "--agreement-rule" in sys.argv:
        score.set_agreement_rule(sys.argv[sys.argv.index("--agreement-rule") + 1])
    main()
