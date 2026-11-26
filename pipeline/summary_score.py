#!/usr/bin/env python3
"""Summary score: the composite and the shared-pool prediction score, with equal weight.

    python3 pipeline/summary_score.py --results out/round2c/results.json --vignettes round2/vignettes_c.json --runs round2c \
        --manifest pipeline/round2/shared_pool_manifest_c.json --answers pipeline/round2/raw/shared_pool_c \
        --provenance pipeline/round2/raw/provenance_pool_c.json --out reports/summary_round2c_numbers.json

Adopted 26 November 2026 at the owner's request ("go ahead with equal weight for the shared-pool score"), AFTER the
round-2c results were known. Under it, Fable moves from third to second in round 2c, and Opus stays first. The weights are
fixed here and apply unchanged to every later round. Both parts stay reported beside the summary. The composite itself is
unchanged, and so is the pilot's results page, which has no shared-pool score.

DEFINITION
  Summary score, 0-100, per author and round:
      0.5 * composite + 0.5 * shared-pool score
  composite: the author's mean composite over its own authored pairs in the round (score.py, author_summary.csv).
  shared-pool score: as defined in pipeline/shared_pool.py (other authors' pairs and the controls, in points).
  The weights are nominal. Expanded into components, the summary is:
      shared-pool prediction 50%, own-pair prediction 20%, confounds 12.5%, originality 10%, comprehension 7.5%.
  No rescaling to the field: an author's summary must not depend on which other authors are in the round. The cost is
  that the part with the wider spread between authors moves the order more. Both spreads are reported.
  Defined only for rounds where every author has a usable shared-pool prediction (round 2c onwards).

ERROR BARS
  Judge level: whole repeats resampled with replacement within each judge group (as in shared_pool.py and
  analyse_c.py). Each pair's gap, verdict and distance prediction score are recomputed, and so is its composite. Only
  the prediction component moves; audits and comprehension are held at their observed values. Every item's gap is
  recomputed for the shared-pool score.
  Item level: pairs resampled with replacement within each author x factor cell, and controls within their type
  (classic, null), so every draw keeps the round's design.
  Combined: each draw pairs a random judge-level resample with an independent item-level resample. The 95% intervals
  and the order frequencies come from these draws.
  A difference between two authors counts as clear only if its combined 95% interval excludes 0.
  Known bias: a pair at full prediction score can only lose under judge resampling, so draws sit below the observed
  summary, more for authors with many pairs at full score. The output reports this shift per author. It largely
  cancels in differences between authors, which is what the "clear" rule uses.
"""
import argparse, itertools, json, os, random, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import score  # noqa: E402
import shared_pool  # noqa: E402

WEIGHTS = {"composite": 0.5, "shared_pool": 0.5}


def q(xs, p):
    xs = sorted(xs)
    return score.pct(xs, p)


def main(a):
    res_in = json.load(open(a.results))
    P = {p["pair_id"]: p for p in res_in["pairs"]}
    V = shared_pool.load_pairs(a.vignettes)
    assert set(P) == set(V), "results and vignettes cover different items"
    man = json.load(open(a.manifest))
    prov = json.load(open(a.provenance))
    preds = {}
    for m, codes in man["models"].items():
        key = next((k for k in prov if k.endswith(":" + m)), None)
        assert key and prov[key].get("usable"), "no usable shared-pool prediction for %s" % m
        ans = json.load(open(os.path.join(a.answers, m + ".json")))["predictions"]
        preds[m] = {codes[x["pair"]]: float(x["gap"]) for x in ans}
    authored = [p for p in P if P[p]["pair_type"] == "authored"]
    tiers = sorted({P[p]["author_tier"] for p in authored})
    assert set(tiers) == set(preds), "every author needs a shared-pool prediction: %s vs %s" % (tiers, sorted(preds))
    items = sorted(P)
    author = {p: (P[p]["author_tier"] if P[p]["pair_type"] == "authored" else None) for p in items}
    wpred = res_in["rules"]["weights"]["prediction"]

    # pairs whose composite does not move with the prediction score (voided prediction or a format cap)
    fixed = {p for p in authored if any(f.startswith("factor not realized") for f in P[p]["flags"]) or P[p]["format_problems"]}

    def pts(m, ids, g):
        return 100 * statistics.mean(max(0.0, 1 - abs(preds[m][p] - g[p]) / shared_pool.SCALE) for p in ids)

    gap_obs = {p: P[p]["effect"]["effect"] for p in items}
    comp_obs = {p: P[p]["composite"] for p in authored}

    def summarise(comp, gap, pick):
        """pick: {tier: list of own pair ids (with repeats)}, others: list of item ids (with repeats) per tier"""
        out = {}
        for t in tiers:
            c = statistics.mean(comp[p] for p in pick["own"][t])
            s = pts(t, pick["others"][t], gap)
            out[t] = {"composite": c, "shared_pool": s, "summary": WEIGHTS["composite"] * c + WEIGHTS["shared_pool"] * s}
        return out

    full = {"own": {t: [p for p in authored if author[p] == t] for t in tiers},
            "others": {t: [p for p in items if author[p] != t] for t in tiers}}
    obs = summarise(comp_obs, gap_obs, full)

    # check: the observed parts match the round's published numbers
    shared_pub = json.load(open(a.shared))["predictors"] if a.shared else None
    for t in tiers:
        if shared_pub:
            assert abs(obs[t]["shared_pool"] - shared_pub[t]["shared_pool_score"]) < 0.051, (t, obs[t]["shared_pool"])

    # judge-level resamples: pair composites and item gaps
    rows = score.load_judgments(os.path.join(ROOT, "judgments.csv"), a.runs)
    units = {}
    for r in rows:
        if r["pair_id"] in P:
            units.setdefault((r["run_id"], r["judge_group"], r["repeat"]), {}).setdefault(r["pair_id"], {}).setdefault(r["version"], []).append(r["rating"])
    groups = sorted({u[1] for u in units})
    rng = random.Random(a.seed)
    judge_draws = []
    for _ in range(a.n_judge):
        cells = {p: {"A": {}, "B": {}} for p in items}
        for g in groups:
            pool = [u for u in units if u[1] == g]
            for u in rng.choices(pool, k=len(pool)):
                for p, vs in units[u].items():
                    for v, xs in vs.items():
                        cells[p][v].setdefault(g, []).extend(xs)
        gap, comp = {}, {}
        for p in items:
            if p in authored and p not in fixed:
                es = score.effect_stats(cells[p], a.n_inner, rng)
                new = score.prediction_score_distance(V[p]["prediction"], score.classify(es), es["effect"], V[p]["pair_type"])["score"]
                comp[p] = comp_obs[p] + 100 * wpred * (new - P[p]["components"]["prediction"])
            elif p in authored:
                comp[p] = comp_obs[p]
            gs = [g for g in cells[p]["A"] if g in cells[p]["B"]]
            gap[p] = statistics.mean(statistics.mean(cells[p]["A"][g]) - statistics.mean(cells[p]["B"][g]) for g in gs)
        judge_draws.append((comp, gap))

    # item-level strata
    strata = {}
    for p in items:
        k = ("authored", author[p], P[p]["factor_id"]) if author[p] else (P[p]["pair_type"],)
        strata.setdefault(k, []).append(p)

    def item_pick():
        chosen = []
        for k, ids in strata.items():
            chosen += rng.choices(ids, k=len(ids))
        return {"own": {t: [p for p in chosen if author[p] == t] for t in tiers},
                "others": {t: [p for p in chosen if author[p] != t] for t in tiers}}

    judge_only = [summarise(c, g, full) for c, g in judge_draws]
    item_only = [summarise(comp_obs, gap_obs, item_pick()) for _ in range(a.n_draws)]
    combined = []
    for _ in range(a.n_draws):
        c, g = judge_draws[rng.randrange(len(judge_draws))]
        combined.append(summarise(c, g, item_pick()))

    def orders(draws):
        o = {}
        for d in draws:
            k = " > ".join(sorted(tiers, key=lambda t: -d[t]["summary"]))
            o[k] = o.get(k, 0) + 1
        return {k: round(v / len(draws), 3) for k, v in sorted(o.items(), key=lambda kv: -kv[1])}

    out = {"definition": "pipeline/summary_score.py docstring", "weights": WEIGHTS, "results": a.results, "runs": a.runs,
           "authors": {}, "spread_between_authors": {}, "pairwise": {}}
    for t in tiers:
        out["authors"][t] = {k: round(obs[t][k], 1) for k in ("composite", "shared_pool", "summary")}
        out["authors"][t]["summary_95"] = [round(q([d[t]["summary"] for d in combined], x), 1) for x in (0.025, 0.975)]
        out["authors"][t]["sd_judge_level"] = round(statistics.pstdev(d[t]["summary"] for d in judge_only), 2)
        out["authors"][t]["sd_item_level"] = round(statistics.pstdev(d[t]["summary"] for d in item_only), 2)
        out["authors"][t]["sd_combined"] = round(statistics.pstdev(d[t]["summary"] for d in combined), 2)
        out["authors"][t]["mean_of_draws_minus_observed"] = round(statistics.mean(d[t]["summary"] for d in combined) - obs[t]["summary"], 2)
    for k in ("composite", "shared_pool"):
        out["spread_between_authors"][k] = {"range": round(max(obs[t][k] for t in tiers) - min(obs[t][k] for t in tiers), 1),
                                            "sd": round(statistics.pstdev(obs[t][k] for t in tiers), 2)}
    out["order_by_summary"] = " > ".join(sorted(tiers, key=lambda t: -obs[t]["summary"]))
    out["order_by_composite"] = " > ".join(sorted(tiers, key=lambda t: -obs[t]["composite"]))
    out["order_by_shared_pool"] = " > ".join(sorted(tiers, key=lambda t: -obs[t]["shared_pool"]))
    out["order_frequencies"] = {"combined": orders(combined), "judge_level_only": orders(judge_only), "item_level_only": orders(item_only)}
    out["first"] = {t: round(sum(1 for d in combined if max(tiers, key=lambda x: d[x]["summary"]) == t) / len(combined), 3) for t in tiers}
    for x, y in itertools.combinations(sorted(tiers, key=lambda t: -obs[t]["summary"]), 2):
        ds = [d[x]["summary"] - d[y]["summary"] for d in combined]
        lo, hi = q(ds, 0.025), q(ds, 0.975)
        out["pairwise"]["%s - %s" % (x, y)] = {"difference": round(obs[x]["summary"] - obs[y]["summary"], 1),
                                               "combined_95": [round(lo, 1), round(hi, 1)], "clear": lo > 0 or hi < 0,
                                               "share_same_sign": round(sum(1 for d in ds if d > 0) / len(ds), 3)}
    out["n"] = {"judge_level": a.n_judge, "inner_bootstrap": a.n_inner, "draws": a.n_draws, "pairs_held_fixed": sorted(fixed)}
    json.dump(out, open(a.out, "w"), indent=1)
    for t in sorted(tiers, key=lambda t: -obs[t]["summary"]):
        x = out["authors"][t]
        print("%-7s summary %5.1f [%5.1f, %5.1f]  = 0.5 x composite %5.1f + 0.5 x shared pool %5.1f   sd judge %.2f item %.2f combined %.2f" % (
            t, x["summary"], x["summary_95"][0], x["summary_95"][1], x["composite"], x["shared_pool"], x["sd_judge_level"],
            x["sd_item_level"], x["sd_combined"]))
    print("spread between authors:", json.dumps(out["spread_between_authors"]))
    print("orders (combined):", json.dumps(out["order_frequencies"]["combined"]))
    print("first:", json.dumps(out["first"]))
    for k, v in out["pairwise"].items():
        print("  %-16s %+5.1f  95%% [%+5.1f, %+5.1f]  same sign %.3f  %s" % (k, v["difference"], v["combined_95"][0], v["combined_95"][1],
                                                                       v["share_same_sign"], "clear" if v["clear"] else "not clear"))
    print("draws minus observed:", {t: out["authors"][t]["mean_of_draws_minus_observed"] for t in tiers})
    print("wrote", os.path.relpath(a.out, ROOT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", required=True)
    ap.add_argument("--vignettes", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--answers", required=True)
    ap.add_argument("--provenance", required=True)
    ap.add_argument("--shared", help="the round's shared-pool numbers, to check the observed scores against")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=20261126)
    ap.add_argument("--n-judge", type=int, default=300)
    ap.add_argument("--n-inner", type=int, default=400)
    ap.add_argument("--n-draws", type=int, default=5000)
    ap.add_argument("--agreement-rule")
    a = ap.parse_args()
    if a.agreement_rule:
        score.set_agreement_rule(a.agreement_rule)
    main(a)
