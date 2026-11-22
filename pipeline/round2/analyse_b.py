#!/usr/bin/env python3
"""Round 2b: does an author's score settle down with three pairs per factor instead of one?

    python3 pipeline/round2/analyse_b.py

Run score.py on round 2b first:
    python3 score.py --vignettes round2/vignettes_b.json --run round2b --audit-run main,round2,round2b --out out/round2b --no-report

Reads out/round2b, out/round2, judgments.csv and round2/vignettes_b.json; writes reports/round2b_numbers.json.

  1. Authors by factor, each on three pairs, and overall on nine.
  2. One pair against three: the round-2 score against the three-pair mean.
  3. How much of the spread in pair scores belongs to the author, and how much to the pair (and a permutation test of
     the author differences, shuffling authors within each factor).
  4. Fragility of the author order: ratings resampled inside each judge-model x version cell, every pair rescored, the
     author means recomputed (the same method as round 2's analysis, now over nine pairs per author).
  5. Test-retest: the round-2 pairs and the ten controls were judged in both round 2 and round 2b, by independent
     persona panels of the same design.
"""
import csv, itertools, json, os, random, statistics, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
import score  # noqa: E402

OUT = os.path.join(ROOT, "reports", "round2b_numbers.json")
NEW = ["inevitable_harm", "knowledge_causation", "luck_wrongness"]
TIERS = ["haiku", "sonnet", "opus"]


def pairs_csv(path):
    return {r["pair_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def f(x):
    return float(x)


def order_key(m):
    return " > ".join(sorted(m, key=lambda t: -m[t]))


def main(n_outer=300, n_inner=400, n_perm=20000, seed=20261123):
    b = pairs_csv(os.path.join(ROOT, "out", "round2b", "pair_scores.csv"))
    r2 = pairs_csv(os.path.join(ROOT, "out", "round2", "pair_scores.csv"))
    V = {p["pair_id"]: p for p in json.load(open(os.path.join(ROOT, "round2", "vignettes_b.json")))["pairs"]}
    authored = {pid: r for pid, r in b.items() if r["pair_type"] == "authored"}
    res = {}

    # 1. authors by factor
    tab, overall = {}, {}
    for t in TIERS:
        tab[t] = {}
        mine = [r for r in authored.values() if r["author_tier"] == t]
        for fac in NEW:
            rr = sorted([r for r in mine if r["factor_id"] == fac], key=lambda r: r["pair_id"])
            tab[t][fac] = {"pairs": {r["pair_id"]: round(f(r["prediction_score"]), 2) for r in rr},
                           "mean_prediction_score": round(statistics.mean(f(r["prediction_score"]) for r in rr), 3),
                           "demonstrated": sum(r["gap_demonstrated"] == "True" for r in rr)}
        overall[t] = {"n_pairs": len(mine),
                      "mean_prediction_score": round(statistics.mean(f(r["prediction_score"]) for r in mine), 3),
                      "mean_composite": round(statistics.mean(f(r["composite"]) for r in mine), 1),
                      "demonstrated": sum(r["gap_demonstrated"] == "True" for r in mine),
                      "full_marks": sum(f(r["prediction_score"]) >= 0.999 for r in mine),
                      "mean_confound_severity": round(statistics.mean(f(r["confound_severity"]) for r in mine), 2),
                      "mean_originality": round(statistics.mean(f(r["originality"]) for r in mine), 2),
                      "predicted_sizes": dict(sorted({s: sum(r["predicted_size"] == s for r in mine)
                                                      for s in ("none", "small", "large")}.items()))}
    res["by_author_and_factor"] = tab
    res["by_author"] = overall
    res["order_by_prediction_score"] = order_key({t: overall[t]["mean_prediction_score"] for t in TIERS})
    res["order_by_composite"] = order_key({t: overall[t]["mean_composite"] for t in TIERS})

    # 2. one pair against three
    one = {}
    for t in TIERS:
        for fac in NEW:
            pid = "r2_%s_%s" % (t, fac)
            one["%s/%s" % (t, fac)] = {"round2_single_pair": round(f(r2[pid]["prediction_score"]), 2),
                                       "same_pair_in_round2b": round(f(b[pid]["prediction_score"]), 2),
                                       "three_pair_mean_round2b": tab[t][fac]["mean_prediction_score"]}
    res["one_pair_vs_three"] = one

    # 3. author vs pair variance, and a permutation test within factors
    ps = {pid: f(r["prediction_score"]) for pid, r in authored.items()}
    grand = statistics.mean(ps.values())
    def between_share(labels):
        groups = {}
        for pid, lab in labels.items():
            groups.setdefault(lab, []).append(ps[pid])
        ssb = sum(len(v) * (statistics.mean(v) - grand) ** 2 for v in groups.values())
        sst = sum((x - grand) ** 2 for x in ps.values())
        return ssb / sst
    by_author = {pid: authored[pid]["author_tier"] for pid in ps}
    by_factor = {pid: authored[pid]["factor_id"] for pid in ps}
    by_cell = {pid: authored[pid]["author_tier"] + "/" + authored[pid]["factor_id"] for pid in ps}
    obs_spread = max(overall[t]["mean_prediction_score"] for t in TIERS) - min(overall[t]["mean_prediction_score"] for t in TIERS)
    rng = random.Random(seed)
    within = {fac: [pid for pid in ps if by_factor[pid] == fac] for fac in NEW}
    hits = 0
    for _ in range(n_perm):
        lab = {}
        for fac, ids in within.items():
            tiers = [by_author[pid] for pid in ids]
            rng.shuffle(tiers)
            lab.update(zip(ids, tiers))
        m = {t: statistics.mean(ps[pid] for pid in ps if lab[pid] == t) for t in TIERS}
        hits += (max(m.values()) - min(m.values())) >= obs_spread - 1e-12
    res["variance"] = {"share_explained_by_author": round(between_share(by_author), 3),
                       "share_explained_by_factor": round(between_share(by_factor), 3),
                       "share_explained_by_author_and_factor_cell": round(between_share(by_cell), 3),
                       "pair_sd_of_prediction_score": round(statistics.pstdev(ps.values()), 3),
                       "author_spread": round(obs_spread, 3),
                       "permutation_p_author_spread": round((hits + 1) / (n_perm + 1), 4),
                       "permutation_note": "authors shuffled among the nine pairs of each factor, %d times; p = share of "
                                           "shuffles whose best-minus-worst author mean is at least the observed one" % n_perm}
    pairwise = {}
    for a, c in itertools.combinations(TIERS, 2):
        ids = [pid for pid in ps if by_author[pid] in (a, c)]
        obs = overall[a]["mean_prediction_score"] - overall[c]["mean_prediction_score"]
        h = 0
        for _ in range(n_perm // 4):
            lab = {}
            for fac in NEW:
                fid = [pid for pid in ids if by_factor[pid] == fac]
                tiers = [by_author[pid] for pid in fid]
                rng.shuffle(tiers)
                lab.update(zip(fid, tiers))
            d = statistics.mean(ps[p] for p in ids if lab[p] == a) - statistics.mean(ps[p] for p in ids if lab[p] == c)
            h += abs(d) >= abs(obs) - 1e-12
        pairwise["%s - %s" % (a, c)] = {"difference": round(obs, 3), "permutation_p": round((h + 1) / (n_perm // 4 + 1), 4)}
    res["pairwise_author_differences"] = pairwise

    # 4. fragility of single pairs and of the author order
    J = score.load_judgments(os.path.join(ROOT, "judgments.csv"), "round2b")
    cells = {}
    for r in J:
        cells.setdefault(r["pair_id"], {"A": {}, "B": {}})[r["version"]].setdefault(r["judge_group"], []).append(r["rating"])
    todo = [pid for pid, p in V.items() if p["pair_type"] in ("authored", "control_classic")]
    assert not any("format" in b[pid]["flags"] for pid in todo), "a format-capped pair: the linear composite shortcut does not hold"
    sim = {pid: [] for pid in todo}
    for _ in range(n_outer):
        for pid in todo:
            p = V[pid]
            pred = p["prediction"]
            c = {v: {g: rng.choices(xs, k=len(xs)) for g, xs in cells[pid][v].items()} for v in "AB"}
            es = score.effect_stats(c, n_inner, rng)
            s = score.prediction_score_distance(pred, score.classify(es), es["effect"], p["pair_type"])
            sim[pid].append(s["score"])
    orders, first, last = {}, {t: 0 for t in TIERS}, {t: 0 for t in TIERS}
    for i in range(n_outer):
        m = {t: statistics.mean(sim[pid][i] for pid in authored if authored[pid]["author_tier"] == t) for t in TIERS}
        k = order_key(m)
        orders[k] = orders.get(k, 0) + 1
        first[k.split(" > ")[0]] += 1
        last[k.split(" > ")[-1]] += 1
    kept = {pid: round(sum(abs(s - f(b[pid]["prediction_score"])) <= 0.25 for s in sim[pid]) / n_outer, 2) for pid in todo}
    res["fragility"] = {
        "method": "as in round 2: %d simulated reruns, %d-draw bootstrap interval inside each" % (n_outer, n_inner),
        "author_order": {k: round(v / n_outer, 3) for k, v in sorted(orders.items(), key=lambda kv: -kv[1])},
        "first": {t: round(v / n_outer, 3) for t, v in first.items()},
        "last": {t: round(v / n_outer, 3) for t, v in last.items()},
        "pair_kept_within_0.25": kept,
        "authored_pairs_kept_below_0.8": sum(1 for pid in authored if kept[pid] < 0.8),
        "author_mean_sd_across_reruns": {t: round(statistics.pstdev(
            statistics.mean(sim[pid][i] for pid in authored if authored[pid]["author_tier"] == t) for i in range(n_outer)), 3)
            for t in TIERS},
    }

    # 5. test-retest against round 2
    shared = [pid for pid in b if pid in r2]
    rows = [{"pair_id": pid, "pair_type": b[pid]["pair_type"], "round2_effect": round(f(r2[pid]["effect"]), 2),
             "round2b_effect": round(f(b[pid]["effect"]), 2), "round2_verdict": r2[pid]["observed_direction"],
             "round2b_verdict": b[pid]["observed_direction"], "round2_score": round(f(r2[pid]["prediction_score"]), 2),
             "round2b_score": round(f(b[pid]["prediction_score"]), 2)} for pid in shared]
    xs, ys = [r["round2_effect"] for r in rows], [r["round2b_effect"] for r in rows]
    res["test_retest"] = {"n_pairs": len(rows), "rows": rows, "effect_correlation": round(statistics.correlation(xs, ys), 3),
                          "mean_abs_effect_difference": round(statistics.mean(abs(x - y) for x, y in zip(xs, ys)), 2),
                          "max_abs_effect_difference": round(max(abs(x - y) for x, y in zip(xs, ys)), 2),
                          "verdict_changes": [r["pair_id"] for r in rows if r["round2_verdict"] != r["round2b_verdict"]],
                          "score_changes_over_0.25": [r["pair_id"] for r in rows if r["pair_type"] != "control_null"
                                                      and abs(r["round2_score"] - r["round2b_score"]) > 0.25]}
    res["controls"] = {pid: {"effect": round(f(r["effect"]), 2), "ci": [round(f(r["ci_low"]), 2), round(f(r["ci_high"]), 2)],
                             "groups_same_sign": int(r["groups_same_sign"]), "observed": r["observed_direction"] + "/" + r["observed_size"],
                             "mean_a": round(f(r["mean_a"]), 2), "mean_b": round(f(r["mean_b"]), 2)}
                       for pid, r in b.items() if r["pair_type"] in ("control_classic", "control_null")}
    json.dump(res, open(OUT, "w"), indent=1)

    print("authors (9 pairs each):")
    for t in TIERS:
        o = overall[t]
        print("  %-7s prediction %.2f  composite %.1f  demonstrated %d/9  full %d  confound %.2f  originality %.2f  sizes %s" % (
            t, o["mean_prediction_score"], o["mean_composite"], o["demonstrated"], o["full_marks"], o["mean_confound_severity"],
            o["mean_originality"], o["predicted_sizes"]))
        print("          " + "  ".join("%s %.2f %s" % (fac, tab[t][fac]["mean_prediction_score"], list(tab[t][fac]["pairs"].values())) for fac in NEW))
    print("one vs three:", json.dumps(one))
    print("variance:", json.dumps(res["variance"]))
    print("pairwise:", json.dumps(pairwise))
    print("order:", json.dumps(res["fragility"]["author_order"]), "first", res["fragility"]["first"], "last", res["fragility"]["last"])
    print("author mean sd across reruns:", res["fragility"]["author_mean_sd_across_reruns"],
          "authored pairs kept < 0.8:", res["fragility"]["authored_pairs_kept_below_0.8"], "of", len(authored))
    tr = res["test_retest"]
    print("test-retest vs round 2: n %d, r %.3f, mean |diff| %.2f, max %.2f; verdict changes %s; score changes %s" % (
        tr["n_pairs"], tr["effect_correlation"], tr["mean_abs_effect_difference"], tr["max_abs_effect_difference"],
        tr["verdict_changes"], tr["score_changes_over_0.25"]))
    for pid, c in res["controls"].items():
        print("  control %-24s %+.2f [%+.2f, %+.2f] %d/3 %s" % (pid, c["effect"], c["ci"][0], c["ci"][1], c["groups_same_sign"], c["observed"]))
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
