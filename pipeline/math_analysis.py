#!/usr/bin/env python3
"""Mathematical analysis of the benchmark on the pilot data.

    python3 pipeline/math_analysis.py            # prints a report, writes reports/math_analysis_numbers.json

Everything here is computed from the pilot data (vignettes.json, judgments.csv,
out/results.json, pipeline/survey_manifest.json) plus clearly labelled
assumptions about human rating noise. Standard library and numpy only.
"""
import csv, itertools, json, math, os, random, statistics, sys
from collections import Counter, defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import score as S  # noqa: E402

OUT = {}
TIERS = ["haiku", "sonnet", "opus", "fable"]
FACTORS = ["intent_accident", "doing_allowing", "knowledge_luck", "moral_luck", "norm_causation"]


def Phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def h(title):
    print("\n" + "=" * 100 + "\n" + title + "\n" + "=" * 100)


R = json.load(open(os.path.join(ROOT, "out", "results.json")))
P = {p["pair_id"]: p for p in R["pairs"]}
authored = [p for p in R["pairs"] if p["pair_type"] == "authored"]
J = S.load_judgments(os.path.join(ROOT, "judgments.csv"), "main")
cells = defaultdict(lambda: {"A": defaultdict(list), "B": defaultdict(list)})
for r in J:
    cells[r["pair_id"]][r["version"]][r["judge_group"]].append(r["rating"])
GROUPS = sorted({r["judge_group"] for r in J})
tier_of_group = {g: next(t for t in TIERS if t in g) for g in GROUPS}


def sign_of(pred):
    return 1 if pred["direction"] == "A_higher" else (-1 if pred["direction"] == "B_higher" else 0)


# ---------------------------------------------------------------------------------------------
h("1. What makes a factor informative about authors")
rows = []
for f in FACTORS:
    ps = [p for p in authored if p["factor_id"] == f]
    gaps = [p["effect"]["effect"] * sign_of(p["prediction"]) for p in ps]   # gap in the author's predicted direction
    cats = [(p["observed"]["direction"], p["observed"]["size"]) for p in ps]
    cnt = Counter(cats)
    H = -sum(c / len(cats) * math.log2(c / len(cats)) for c in cnt.values())
    scores = [p["components"]["prediction"] for p in ps]
    rows.append({"factor": f, "gaps_in_predicted_direction": [round(g, 2) for g in gaps], "mean_gap": statistics.mean(gaps),
                 "sd_gap": statistics.stdev(gaps), "outcome_entropy_bits": H, "distinct_outcomes": len(cnt),
                 "prediction_scores": scores, "sd_prediction_score": statistics.pstdev(scores)})
    print("%-16s gaps %-28s mean %+.2f sd %.2f | outcome categories %d, entropy %.2f bits | prediction scores %s" % (
        f, [round(g, 2) for g in gaps], statistics.mean(gaps), statistics.stdev(gaps), len(cnt), H, scores))
allg = [g for r in rows for g in r["gaps_in_predicted_direction"]]
grand = statistics.mean(allg)
ss_tot = sum((g - grand) ** 2 for g in allg)
ss_fac = sum(4 * (r["mean_gap"] - grand) ** 2 for r in rows)
alls = [s for r in rows for s in r["prediction_scores"]]
gs = statistics.mean(alls)
ss_tot_s = sum((s - gs) ** 2 for s in alls)
ss_fac_s = sum(4 * (statistics.mean(r["prediction_scores"]) - gs) ** 2 for r in rows)
print("share of the variance in gaps explained by the factor alone: %.0f%%" % (100 * ss_fac / ss_tot))
print("share of the variance in prediction scores explained by the factor alone: %.0f%%" % (100 * ss_fac_s / ss_tot_s))
OUT["factor_informativeness"] = {"rows": rows, "gap_variance_share_factor": ss_fac / ss_tot,
                                 "score_variance_share_factor": ss_fac_s / ss_tot_s}
# naive baselines that know only the textbook direction, or only what other authors got on the same factor
base = {}
for label, size in (("textbook direction, always 'large'", "large"), ("textbook direction, always 'small'", "small")):
    sc = [S.prediction_score({"direction": p["prediction"]["direction"], "size": size}, p["observed"], p["effect"]["effect"])["score"] for p in authored]
    base[label] = statistics.mean(sc)
loo = []
for p in authored:
    others = [q for q in authored if q["factor_id"] == p["factor_id"] and q["pair_id"] != p["pair_id"]]
    c = Counter((q["observed"]["direction"], q["observed"]["size"]) for q in others).most_common(1)[0][0]
    guess = {"direction": c[0], "size": c[1]} if c[0] in ("A_higher", "B_higher", "none") else p["prediction"]
    if guess["direction"] in ("A_higher", "B_higher"):
        # translate 'A/B higher' into the same side as this pair's textbook direction
        guess = {"direction": p["prediction"]["direction"], "size": guess["size"]}
    loo.append(S.prediction_score(guess, p["observed"], p["effect"]["effect"])["score"])
base["what other authors got on the same factor"] = statistics.mean(loo)
base["the authors themselves"] = statistics.mean(p["components"]["prediction"] for p in authored)
for k, v in base.items():
    print("mean prediction score, %-45s %.2f" % (k + ":", v))
OUT["baselines"] = base

# ---------------------------------------------------------------------------------------------
h("2. Is the prediction score proper, and what does it elicit?")
CATS = ["B_large", "B_small", "none", "A_small", "A_large"]


def obs_of(cat):
    if cat == "none":
        return {"direction": "none", "size": "none"}, 0.0
    d, s = cat.split("_")
    return {"direction": d + "_higher", "size": s}, (1.0 if d == "A" else -1.0)


def pred_of(cat):
    if cat == "none":
        return {"direction": "none", "size": "none"}
    d, s = cat.split("_")
    return {"direction": d + "_higher", "size": s}


M = [[S.prediction_score(pred_of(rc), *obs_of(oc))["score"] for oc in CATS] for rc in CATS]
print("score matrix (rows = report, columns = observed):")
print("            " + "".join("%9s" % c for c in CATS))
for rc, row in zip(CATS, M):
    print("%-12s" % rc + "".join("%9.2f" % x for x in row))
rng = np.random.default_rng(1)
B = rng.dirichlet(np.ones(5), size=200000)
Mm = np.array(M)
exp_scores = B @ Mm.T
bayes = exp_scores.argmax(1)
mode = B.argmax(1)
cdf = B.cumsum(1)
median = (cdf >= 0.5).argmax(1)
print("random beliefs over the five outcomes: the best report is the most likely outcome in %.0f%% of cases, the median outcome in %.0f%%" % (
    100 * (bayes == mode).mean(), 100 * (bayes == median).mean()))
# a concrete example
ex = np.array([0, 0, 0.25, 0.30, 0.45])
print("example belief (none .25, A_small .30, A_large .45): expected score per report",
      {c: round(float(v), 3) for c, v in zip(CATS, ex @ Mm.T)})
OUT["scoring_rule"] = {"matrix": M, "share_bayes_equals_mode": float((bayes == mode).mean()),
                       "share_bayes_equals_median": float((bayes == median).mean())}

# ---------------------------------------------------------------------------------------------
h("3. How noisy is a human verdict on one pair? (assumption: rating SD 1.5 on the 1-7 scale)")
Z = 1.96


def outcome_probs(delta, se, z=Z):
    """Probabilities of each classification of one pair under the pre-set rule, normal approximation."""
    t = z * se
    def p(a, b):
        return max(0.0, Phi((b - delta) / se) - Phi((a - delta) / se))
    lo = max(0.5, t)
    pr = {"none": p(-0.5, 0.5)}
    pr["A_small"] = p(lo, 1.5) if lo < 1.5 else 0.0
    pr["A_large"] = p(max(1.5, t), 1e9)
    pr["B_small"] = p(-1.5, -lo) if lo < 1.5 else 0.0
    pr["B_large"] = p(-1e9, -max(1.5, t))
    pr["A_unclear"] = p(0.5, max(0.5, t)) if t > 0.5 else 0.0
    pr["B_unclear"] = p(-max(0.5, t), -0.5) if t > 0.5 else 0.0
    return pr


def true_cat(delta):
    a = abs(delta)
    if a < 0.5:
        return "none"
    return ("A" if delta > 0 else "B") + ("_small" if a < 1.5 else "_large")


def expected_oracle_score(delta, se):
    """Expected prediction score of an author who knows the true gap exactly and reports its category."""
    rep = pred_of(true_cat(delta))
    tot = 0.0
    for k, pk in outcome_probs(delta, se).items():
        if k.endswith("unclear"):
            # unclear outcomes still carry a size; approximate with the size of the true gap
            size = "small" if abs(delta) < 1.5 else "large"
            obs, eff = {"direction": "unclear", "size": size}, (1.0 if k[0] == "A" else -1.0)
        else:
            obs, eff = obs_of(k)
        tot += pk * S.prediction_score(rep, obs, eff)["score"]
    return tot


SIGMA = 1.5
NS = [8, 20, 40, 80]
DELTAS = [0.0, 0.5, 0.75, 1.0, 1.25, 1.75, 2.0, 3.0]
tab = {}
print("Probability that the pair is classified in its TRUE category, and the expected score of an author who knows the truth:")
print("true gap  " + "".join("   n=%-3d per version (SE %.2f)   " % (n, SIGMA * math.sqrt(2 / n)) for n in NS))
for d in DELTAS:
    line = "%+5.2f     " % d
    for n in NS:
        se = SIGMA * math.sqrt(2 / n)
        pr = outcome_probs(d, se)
        right = pr[true_cat(d)] if true_cat(d) != "none" else pr["none"]
        line += "   P(right)=%.2f  oracle=%.2f      " % (right, expected_oracle_score(d, se))
        tab.setdefault(str(n), {})[str(d)] = {"p_true_category": right, "oracle_expected_score": expected_oracle_score(d, se), **pr}
    print(line)
for n in NS:
    se = SIGMA * math.sqrt(2 / n)
    print("n=%-3d: a gap must exceed %.2f points before its interval excludes zero; the 'small' bin (0.5-1.5) is %s" % (
        n, Z * se, "unreachable" if Z * se >= 1.5 else ("reachable only above %.2f" % max(0.5, Z * se))))
for icc in (0.1, 0.2, 0.3):
    print("if %.0f%% of rating variance is a participant's general leniency, a model with a participant effect cuts the standard error by %.0f%%" % (
        100 * icc, 100 * (1 - math.sqrt(1 - icc))))
for d in (0.5, 1.0):
    print("people per version needed before a true gap of %.1f can be confirmed half the time: about %d (SD 1.5), %d (SD 1.2)" % (
        d, math.ceil(2 * (Z * 1.5 / d) ** 2), math.ceil(2 * (Z * 1.2 / d) ** 2)))
OUT["human_noise"] = {"sigma_assumed": SIGMA, "table": tab}

# ---------------------------------------------------------------------------------------------
h("4. Does the calibration bar I proposed make sense?")
# bar: same verdict on >= 24 of 30 pairs. Suppose people's true gaps equal the model panel's gaps (k = 1) or half of them (k = 0.5).
model_cat = {}
for pid, p in P.items():
    o = p["observed"]
    model_cat[pid] = "none" if o["size"] == "none" else ((o["direction"][0] + "_" + o["size"]) if o["direction"] != "unclear" else "unclear")


def poisson_binomial_tail(ps, k):
    dist = [1.0]
    for p in ps:
        new = [0.0] * (len(dist) + 1)
        for i, q in enumerate(dist):
            new[i] += q * (1 - p)
            new[i + 1] += q * p
        dist = new
    return sum(dist[k:]), sum(i * q for i, q in enumerate(dist))


bar = {}
for k in (1.0, 0.5):
    for n in NS:
        se = SIGMA * math.sqrt(2 / n)
        ps = []
        for pid, p in P.items():
            pr = outcome_probs(k * p["effect"]["effect"], se)
            ps.append(pr.get(model_cat[pid], 0.0))
        tail, mean_agree = poisson_binomial_tail(ps, 24)
        bar["k=%s,n=%d" % (k, n)] = {"expected_agreements": mean_agree, "p_at_least_24": tail}
        print("people's true gaps = %.1f x panel's, n=%-3d per version: expected same verdicts %.1f of 30, P(>=24) = %.3f" % (k, n, mean_agree, tail))
for n in NS:
    se = SIGMA * math.sqrt(2 / n)
    p0 = 1 - outcome_probs(0.0, se)["none"] - outcome_probs(0.0, se)["A_unclear"] - outcome_probs(0.0, se)["B_unclear"]
    print("n=%-3d: chance a truly null pair shows a confirmed gap %.3f; chance at least one of the 5 null controls does %.2f" % (n, p0, 1 - (1 - p0) ** 5))
    bar["null_n=%d" % n] = {"per_pair": p0, "any_of_5": 1 - (1 - p0) ** 5}
OUT["calibration_bar"] = bar

# moral-luck classic control in people: Kneer & Machery (2019) report blame d about 0.33-0.39, SD about 1.5-2.0
for d_std in (0.33, 0.39):
    for n in NS:
        se = SIGMA * math.sqrt(2 / n)
        pr = outcome_probs(d_std * SIGMA, se)
        print("moral-luck control with d=%.2f (gap %.2f): n=%-3d P(confirmed in the expected direction) = %.2f" % (
            d_std, d_std * SIGMA, n, pr["A_small"] + pr["A_large"]))

# ---------------------------------------------------------------------------------------------
h("5. Looking at the results as participants arrive")
rng2 = random.Random(7)
looks = [4, 8, 12, 16, 20, 30, 40]
trials, hit_any, hit_last = 20000, 0, 0
for _ in range(trials):
    a = [rng2.gauss(0, SIGMA) for _ in range(40)]
    b = [rng2.gauss(0, SIGMA) for _ in range(40)]
    seen = False
    for n in looks:
        d = statistics.fmean(a[:n]) - statistics.fmean(b[:n])
        se = math.sqrt(statistics.variance(a[:n]) / n + statistics.variance(b[:n]) / n)
        conf = abs(d) >= 0.5 and abs(d) > Z * se
        if conf:
            seen = True
        if n == 40 and conf:
            hit_last += 1
    hit_any += seen
print("null pair, rule applied once at n=40: false gap %.3f; applied at every look %s: false gap at some look %.3f" % (
    hit_last / trials, looks, hit_any / trials))
OUT["peeking"] = {"single_look": hit_last / trials, "seven_looks": hit_any / trials}

# ---------------------------------------------------------------------------------------------
h("6. Same-model effect: judges on their own author's pairs")
obs_rows = []
for p in authored:
    sg = sign_of(p["prediction"])
    for g in GROUPS:
        a, b = cells[p["pair_id"]]["A"][g], cells[p["pair_id"]]["B"][g]
        obs_rows.append((p["pair_id"], g, sg * (statistics.mean(a) - statistics.mean(b)), int(tier_of_group[g] == p["author_tier"])))
pids = sorted({r[0] for r in obs_rows})


def fit(rows):
    pidx = {pid: i for i, pid in enumerate(sorted({r[0] for r in rows}))}
    gidx = {g: i for i, g in enumerate(GROUPS)}
    X, y = [], []
    for pid, g, val, own in rows:
        x = [0.0] * (len(pidx) + len(GROUPS) - 1 + 1)
        x[pidx[pid]] = 1.0
        if gidx[g] > 0:
            x[len(pidx) + gidx[g] - 1] = 1.0
        x[-1] = own
        X.append(x)
        y.append(val)
    beta, *_ = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)
    return beta[-1]


b_hat = fit(obs_rows)
rng3 = random.Random(3)
boots = []
by_pair = defaultdict(list)
for r in obs_rows:
    by_pair[r[0]].append(r)
for _ in range(4000):
    samp = []
    for j, pid in enumerate(rng3.choices(pids, k=len(pids))):
        samp += [(pid + "#%d" % j, g, v, o) for (_, g, v, o) in by_pair[pid]]
    try:
        boots.append(fit(samp))
    except Exception:
        pass
boots.sort()
print("own-model effect, controlling for each pair and each judge model: %+.2f points (95%% interval %+.2f to %+.2f)" % (
    b_hat, boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]))
# leave-own-model-out rescoring
changed = []
for p in authored:
    c = {"A": {g: v for g, v in cells[p["pair_id"]]["A"].items() if tier_of_group[g] != p["author_tier"]},
         "B": {g: v for g, v in cells[p["pair_id"]]["B"].items() if tier_of_group[g] != p["author_tier"]}}
    es = S.effect_stats(c, 4000, random.Random(11))
    ob = S.classify(es)
    ps = S.prediction_score(p["prediction"], ob, es["effect"])["score"]
    if (ob["direction"], ob["size"]) != (p["observed"]["direction"], p["observed"]["size"]):
        changed.append((p["pair_id"], "%s/%s -> %s/%s" % (p["observed"]["direction"], p["observed"]["size"], ob["direction"], ob["size"]),
                        "%.2f -> %.2f" % (p["components"]["prediction"], ps)))
print("leaving out the author's own model changes the verdict on %d of 20 authored pairs:" % len(changed))
for c in changed:
    print("   ", c)
OUT["same_model"] = {"beta": b_hat, "ci": [boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots))]], "changed_without_own": changed}

# ---------------------------------------------------------------------------------------------
h("7. Can the pilot rank its authors?")
score_of = {(p["author_tier"], p["factor_id"]): p["components"]["prediction"] for p in authored}
comp_of = {(p["author_tier"], p["factor_id"]): p["composite"] for p in authored}


def spread(table, perm=None):
    means = []
    for i, t in enumerate(TIERS):
        vals = []
        for f in FACTORS:
            src = perm[f][i] if perm else t
            vals.append(table[(src, f)])
        means.append(statistics.mean(vals))
    return statistics.pvariance(means), means


for name, table in (("prediction score", score_of), ("composite", comp_of)):
    v_obs, means = spread(table)
    rng4 = random.Random(5)
    ge = 0
    for _ in range(20000):
        perm = {f: rng4.sample(TIERS, 4) for f in FACTORS}
        if spread(table, perm)[0] >= v_obs - 1e-12:
            ge += 1
    print("%-16s author means %s | permutation p = %.2f (shuffling authors within each factor)" % (
        name, dict(zip(TIERS, [round(m, 2) for m in means])), ge / 20000))
    OUT.setdefault("authors", {})[name] = {"means": dict(zip(TIERS, means)), "perm_p": ge / 20000}
sd_within = math.sqrt(statistics.mean([statistics.pvariance([score_of[(t, f)] for t in TIERS]) for f in FACTORS]))
for delta in (0.1, 0.2):
    n_pairs = math.ceil(2 * (1.96 + 0.84) ** 2 * sd_within ** 2 / delta ** 2)
    print("pairs per author needed to detect a difference of %.1f in mean prediction score (within-factor SD %.2f, 80%% power): %d" % (
        delta, sd_within, n_pairs))
OUT["authors"]["sd_within_factor"] = sd_within

# ---------------------------------------------------------------------------------------------
h("8. What one survey participant sees: both sides of each factor")
man = json.load(open(os.path.join(HERE, "survey_manifest.json")))
doc = json.load(open(os.path.join(ROOT, "vignettes.json"), encoding="utf-8"))
dirn = {}
for p in doc["pairs"]:
    if p["pair_type"] == "control_null":
        continue
    hi = "A" if p["prediction"]["direction"] == "A_higher" else "B"
    dirn[p["pair_id"]] = (p["factor_id"], hi)
both_sides = Counter()
per_factor_counts = []
for form, codes in man["forms"].items():
    seen = defaultdict(lambda: [0, 0])
    for c in codes:
        it = man["items"][c]
        if it["pair_id"] in dirn:
            f, hi = dirn[it["pair_id"]]
            seen[f][0 if it["version"] == hi else 1] += 1
    for f in FACTORS:
        if seen[f][0] and seen[f][1]:
            both_sides[f] += 1
        per_factor_counts.append(tuple(seen[f]))
print("forms (of %d) in which a participant meets both the high-rating and the low-rating side of a factor:" % len(man["forms"]))
for f in FACTORS:
    print("   %-16s %d" % (f, both_sides[f]))
clusters = {"freezer (intention)": ["au_sonnet_intent_accident", "au_fable_intent_accident"],
            "greenhouse (doing/allowing)": ["au_sonnet_doing_allowing", "au_opus_doing_allowing"]}
for name, pair_ids in clusters.items():
    k = 0
    for form, codes in man["forms"].items():
        sides = set()
        for c in codes:
            it = man["items"][c]
            if it["pair_id"] in pair_ids:
                sides.add(it["version"] == dirn[it["pair_id"]][1])
        k += len(sides) == 2
    print("forms that show one %s story in its high version and the other in its low version: %d of %d" % (name, k, len(man["forms"])))
OUT["survey_exposure"] = {"both_sides": dict(both_sides)}

# ---------------------------------------------------------------------------------------------
h("9. The ceiling: how a bounded 1-7 scale compresses gaps (ordered-probit illustration, latent SD 1.5)")


def mean_rating(mu, sd=1.5):
    return 1 + sum(Phi((mu - t) / sd) for t in (1.5, 2.5, 3.5, 4.5, 5.5, 6.5))


for base in (3.0, 4.0, 5.0, 6.0, 6.5):
    obs1 = mean_rating(base + 1.0) - mean_rating(base)
    print("latent shift of 1.0 point upward from a latent level of %.1f shows up as an observed gap of %.2f" % (base, obs1))
hi_means = [max(p["effect"]["mean_a"], p["effect"]["mean_b"]) for p in authored if p["factor_id"] in ("intent_accident", "knowledge_luck")]
print("pilot: in the intention and knowledge pairs the higher version averages %.2f of 7 (range %.2f-%.2f)" % (
    statistics.mean(hi_means), min(hi_means), max(hi_means)))

# ---------------------------------------------------------------------------------------------
h("10. Using the model panel as a surrogate once human data exist")
for rho in (0.5, 0.7, 0.8, 0.9, 0.95):
    print("correlation %.2f between panel and people across pairs -> a human sample is worth %.1f times its size when combined with the panel" % (
        rho, 1 / (1 - rho ** 2)))
xs = [p["effect"]["effect"] for p in R["pairs"]]
sxx = sum((x - statistics.mean(xs)) ** 2 for x in xs)
for n in NS:
    se = SIGMA * math.sqrt(2 / n)
    for tau in (0.25, 0.5):
        print("n=%-3d per version, pair-level disagreement SD %.2f: standard error of the calibration slope %.3f" % (
            n, tau, math.sqrt((tau ** 2 + se ** 2) / sxx)))

os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
json.dump(OUT, open(os.path.join(ROOT, "reports", "math_analysis_numbers.json"), "w"), indent=1, default=float)
print("\nwrote reports/math_analysis_numbers.json")
