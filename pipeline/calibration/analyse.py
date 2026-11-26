#!/usr/bin/env python3
"""Compare the model panel's judgments with published human judgments on the same stories.

    python3 pipeline/calibration/analyse.py --answers DIR --moral-evals DIR --moca DIR \
        [--recognition DIR --recognition-key FILE] [--provenance FILE] [--out FILE]

Inputs
  answers       one JSON file per judge (bNN.json), as written by the calibration judges
  moral-evals   clone of cicl-stanford/moral-evals (OffTheRails, Experiment 2 human ratings)
  moca          clone of cicl-stanford/moca (MoCa causal and moral datasets, 25 votes per story)
  recognition   optional: {model}.json answers to "do you recognise this story?" plus the item key
  manifest      pipeline/calibration/manifest.json (which item sat at which batch position)

What it computes (all story texts stay out of the output; only ids and numbers)
  OffTheRails: for each of 10 scenarios and each of 3 factors (harm as a means vs a side effect,
    harm evitable vs inevitable, action vs omission) the gap in mean rating between the two levels,
    pooled over the other two factors, on both questions (permissibility, intention): 60 contrasts.
    Humans: 115 workers x 16 ratings; intervals resample workers. Panel: 4 models x 10 judges x 10
    ratings; the panel gap is the mean of the four per-model gaps, as in score.py.
    The benchmark's confirmed-gap rule is applied to each panel contrast (|gap| >= 0.5 on the 1-7
    scale, rescaled here to the 1-5 scale; 95% interval excludes 0; >= 75% of models agree in sign),
    and each verdict is checked against the human data.
  MoCa: 85 near-minimal story pairs (same question, >= 85% word overlap). Gap in the share of "yes"
    answers, panel against human (25 votes per story).
  Agreement statistics: correlation, slope, inflation, sign agreement where humans show a clear gap,
  false-positive rate where they do not, and correlations corrected for the measured reliability of
  each side (random split halves).
"""
import argparse, ast, csv, glob, json, math, os, random, re, statistics
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("--answers", required=True)
ap.add_argument("--moral-evals", required=True)
ap.add_argument("--moca", required=True)
ap.add_argument("--recognition")
ap.add_argument("--recognition-key")
ap.add_argument("--provenance", help="output of check_judges.py --out; batches it marks unusable are dropped")
ap.add_argument("--manifest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json"))
ap.add_argument("--out")
ap.add_argument("--boot", type=int, default=2000)
ap.add_argument("--splits", type=int, default=200)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--group", action="append", default=[], metavar="LABEL=DIR",
                help="an extra judge group (e.g. another vendor's model) whose bNN.json answers in DIR follow the manifest's batches")
ap.add_argument("--agreement-rule", choices=["three_quarters", "two_thirds", "ceiling_abstain"], default="three_quarters",
                help="share of panel groups that must agree on a gap's sign: three_quarters (the pilot's rule, and the "
                     "default here so the published calibration numbers rebuild unchanged), two_thirds (the benchmark's "
                     "rule from 24 November 2026: 2 of 3 groups, 3 of 4) or ceiling_abstain (three quarters of the voting "
                     "groups, at least two; a group whose mean for both sides lies in the top or bottom twelfth of the "
                     "scale abstains, as in score.py)")
ap.add_argument("--panel", help="comma-separated groups that form the panel (default: the manifest's four Claude models)")
args = ap.parse_args()
rng = random.Random(args.seed)
man = json.load(open(args.manifest))
EXTRA = dict(g.split("=", 1) for g in args.group)
MODELS = args.panel.split(",") if args.panel else man["models"]
for m in MODELS:
    if m not in man["models"] and m not in EXTRA:
        raise SystemExit("panel group %s has no answers (add --group %s=DIR)" % (m, m))
OTR_THRESHOLD = 0.5 * 4 / 6          # the benchmark's 0.5 on a 1-7 scale, as a share of the scale's range, on 1-5
MOCA_THRESHOLD = 0.25                # yes-share gap treated as "confirmed size" for MoCa (no benchmark analogue)
AGREE_SHARE = {"three_quarters": 0.75, "two_thirds": 2 / 3, "ceiling_abstain": 0.75}[args.agreement_rule]
ABSTAIN = args.agreement_rule == "ceiling_abstain"
BOUND_SHARE = 1 / 12                 # as in score.py: the top or bottom twelfth of the scale's range (6.5 or 1.5 on 1-7)
OTR_SCALE, MOCA_SCALE = (1, 5), (0, 1)


def agrees(same, n):
    """Enough panel groups share the sign: the share, rounded up to whole groups, as in score.py."""
    if ABSTAIN and n < 2:
        return False
    return same >= math.ceil(AGREE_SHARE * n - 1e-9)


def at_bound(a, b, scale):
    lo_b = scale[0] + BOUND_SHARE * (scale[1] - scale[0])
    hi_b = scale[1] - BOUND_SHARE * (scale[1] - scale[0])
    return min(a, b) >= hi_b - 1e-9 or max(a, b) <= lo_b + 1e-9


def votes(per, d, sides=None, scale=None):
    """(groups agreeing in sign with d, groups voting). Under ceiling_abstain a group whose two side means both lie at
    the top or the bottom of the scale abstains."""
    voters = [m for m in per if not (ABSTAIN and sides and m in sides and at_bound(sides[m][0], sides[m][1], scale))]
    return sum(1 for m in voters if d and per[m] * d > 0), len(voters)


HUMAN_CLEAR = 0.30                   # MoCa: human yes-share gap counted as clear for direction agreement
FACTORS = [("means_minus_side_effect", "cs"), ("evitable_minus_inevitable", "ev"), ("action_minus_omission", "ac")]
QUESTIONS = ["permissibility", "intention"]


def mean(x):
    return sum(x) / len(x)


def pct(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = math.floor(k)
    c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def pearson(x, y):
    mx, my = mean(x), mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else float("nan")


def ols_slope(x, y):
    mx, my = mean(x), mean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx if sxx else float("nan")


def r3(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(v, 3)


def agreement(panel, human, human_clear):
    """panel, human: lists of gaps; human_clear: list of bools (human gap clearly non-zero)."""
    out = {"n": len(panel), "pearson_r": r3(pearson(panel, human)),
           "slope_panel_on_human": r3(ols_slope(human, panel)),
           "slope_through_origin": r3(sum(p * h for p, h in zip(panel, human)) / sum(h * h for h in human)),
           "mean_abs_gap_panel": r3(mean([abs(p) for p in panel])),
           "mean_abs_gap_human": r3(mean([abs(h) for h in human]))}
    out["inflation_mean_abs"] = r3(out["mean_abs_gap_panel"] / out["mean_abs_gap_human"])
    clear = [(p, h) for p, h, c in zip(panel, human, human_clear) if c]
    out["n_human_clear"] = len(clear)
    if clear:
        # where humans show a clear gap: the panel's gap has the same sign, is exactly zero (a tie), or is opposite
        out["where_human_clear"] = {"same_sign": r3(mean([1.0 if p * h > 0 else 0.0 for p, h in clear])),
                                    "panel_zero": r3(mean([1.0 if p == 0 else 0.0 for p, h in clear])),
                                    "opposite": r3(mean([1.0 if p * h < 0 else 0.0 for p, h in clear]))}
    return out


# ------------------------------------------------------------------ provenance
usable = set(man["batches"])
excluded = {}
if args.provenance:
    prov = json.load(open(args.provenance))
    for bid, r in prov.items():
        if r.get("answers") != "ok" or not r.get("usable", r.get("clean_tool_use")):
            usable.discard(bid)
            excluded[bid] = r.get("answers") if r.get("answers") != "ok" else "tool use"

# ------------------------------------------------------------------ panel answers
P_otr, P_moca = [], []
sources = [(info["model"], bid, os.path.join(args.answers, bid + ".json")) for bid, info in sorted(man["batches"].items())
           if bid in usable]
for label, d in EXTRA.items():
    missing = []
    for bid in sorted(man["batches"]):
        f = os.path.join(d, bid + ".json")
        if os.path.exists(f):
            sources.append((label, label + ":" + bid, f))
        else:
            missing.append(bid)
    if missing:
        excluded[label] = "no answers for " + " ".join(missing)
for group, judge, f in sources:
    if group not in MODELS:
        continue
    bid = judge.split(":")[-1]
    info = man["batches"][bid]
    a = json.load(open(f))
    p1 = {int(x["item"]): x for x in a["part1"]}
    for i, it in enumerate(info["part1"], 1):
        c = it["condition"]
        P_otr.append({"model": group, "judge": judge, "arm": info["arm"], "s": it["scenario_id"],
                      "cs": 1 if c.startswith("cc_") else 0, "ev": 1 if "_evitable_" in c else 0,
                      "ac": 1 if c.endswith("action_yes") else 0,
                      "permissibility": int(p1[i]["statement1"]), "intention": int(p1[i]["statement2"])})
    p2 = {int(x["item"]): x for x in a["part2"]}
    for i, sid in enumerate(info["part2"], 1):
        P_moca.append({"model": group, "judge": judge, "arm": info["arm"], "story": sid,
                       "yes": 1 if str(p2[i]["answer"]).strip().lower() == "yes" else 0})

# ------------------------------------------------------------------ human OffTheRails (Experiment 2)
exp2 = os.path.join(args.moral_evals, "offtherails", "prolific-exp-2")
batch_conds = {}
for f in glob.glob(os.path.join(exp2, "batch_*.json")):
    k = int(re.search(r"batch_(\d+)", f).group(1))
    batch_conds[k] = sorted((x["scenario_id"], x["condition"]) for x in json.load(open(f, encoding="utf-8")))
# Coding of the long-format columns, recovered by matching every worker's 16 rows to the batch file
# their split names: causal_structure 1 = cc ("as a means to"), 0 = coc ("as a side effect");
# evitability 1 = evitable, 0 = inevitable; action 1 = action_yes (acts), 0 = prevention_no (does not prevent).
CODE = ({0: "coc", 1: "cc"}, {0: "inevitable", 1: "evitable"}, {0: "prevention_no", 1: "action_yes"})
H = []
by_worker = defaultdict(list)
for r in csv.DictReader(open(os.path.join(exp2, "data_long_format.csv"), encoding="utf-8")):
    by_worker[r["worker_id"]].append(r)
worker_match = {}
for w, rows in by_worker.items():
    coded = sorted((int(r["scenario_id"]), "%s_%s_%s" % (CODE[0][int(r["causal_structure"])], CODE[1][int(r["evitability"])],
                                                         CODE[2][int(r["action"])])) for r in rows)
    worker_match[w] = coded == batch_conds.get(int(rows[0]["split"]))
    seen = set()
    for order, r in enumerate(rows):     # rows are taken to be in presentation order (see report)
        s = int(r["scenario_id"])
        H.append({"worker": w, "s": s, "cs": int(r["causal_structure"]), "ev": int(r["evitability"]), "ac": int(r["action"]),
                  "permissibility": int(r["permissibility_rating"]), "intention": int(r["intention_rating"]),
                  "first_exposure": s not in seen, "matches_batch": worker_match[w]})
        seen.add(s)
workers = sorted(by_worker)

SCEN = sorted({x["s"] for x in H})
CONTRASTS = [(s, fname, fkey, q) for fname, fkey in FACTORS for q in QUESTIONS for s in SCEN]


def side_means(rows, weights=None):
    """{(s, fkey, side, q): (sum, n)} from rating rows; weights maps worker or judge to a multiplicity."""
    acc = defaultdict(lambda: [0.0, 0.0])
    for x in rows:
        w = 1.0 if weights is None else weights.get(x.get("worker", x.get("judge")), 0)
        if not w:
            continue
        for _, fkey in FACTORS:
            for q in QUESTIONS:
                a = acc[(x["s"], fkey, x[fkey], q)]
                a[0] += w * x[q]
                a[1] += w
    return acc


def gaps_from(acc):
    out = {}
    for s, fname, fkey, q in CONTRASTS:
        a, b = acc.get((s, fkey, 1, q)), acc.get((s, fkey, 0, q))
        if a and b and a[1] and b[1]:
            out[(s, fname, q)] = a[0] / a[1] - b[0] / b[1]
    return out


def human_gaps(rows, weights=None):
    return gaps_from(side_means(rows, weights))


def panel_gaps(rows, judge_weights=None):
    """Mean over models of each model's own gap (equal weight per model, as in score.py)."""
    per_model = {m: gaps_from(side_means([x for x in rows if x["model"] == m], judge_weights)) for m in MODELS}
    out, per = {}, {}
    for key in {k for g in per_model.values() for k in g}:
        vals = {m: per_model[m][key] for m in MODELS if key in per_model[m]}
        per[key] = vals
        out[key] = mean(list(vals.values()))
    return out, per


def cluster_weights(units, r):
    w = defaultdict(int)
    for u in r.choices(units, k=len(units)):
        w[u] += 1
    return w


# point estimates
hg = human_gaps(H)
pg, pg_per = panel_gaps(P_otr)
pg_sides = defaultdict(dict)          # per-model mean of each side, for ceiling abstention
for m in MODELS:
    acc_m = side_means([x for x in P_otr if x["model"] == m])
    for s, fname, fkey, q in CONTRASTS:
        a, b = acc_m.get((s, fkey, 1, q)), acc_m.get((s, fkey, 0, q))
        if a and b and a[1] and b[1]:
            pg_sides[(s, fname, q)][m] = (a[0] / a[1], b[0] / b[1])

# human intervals: resample workers
hboot = defaultdict(list)
for _ in range(args.boot):
    g = human_gaps(H, cluster_weights(workers, rng))
    for k, v in g.items():
        hboot[k].append(v)
hci = {k: (pct(v, 0.025), pct(v, 0.975)) for k, v in hboot.items()}

# panel intervals for each contrast: the benchmark's stratified bootstrap (ratings resampled inside each
# model x side cell). Inside one scenario a judge gives one rating, so ratings are independent here.
cells = defaultdict(list)
for x in P_otr:
    for _, fkey in FACTORS:
        for q in QUESTIONS:
            cells[(x["s"], fkey, x[fkey], q, x["model"])].append(x[q])
pci = {}
for s, fname, fkey, q in CONTRASTS:
    A = [cells[(s, fkey, 1, q, m)] for m in MODELS]
    B = [cells[(s, fkey, 0, q, m)] for m in MODELS]
    boots = []
    for _ in range(args.boot):
        boots.append(mean([mean(rng.choices(a, k=len(a))) - mean(rng.choices(b, k=len(b))) for a, b in zip(A, B)]))
    pci[(s, fname, q)] = (pct(boots, 0.025), pct(boots, 0.975))


def panel_verdict(key):
    d = pg[key]
    lo, hi = pci[key]
    same, n = votes(pg_per[key], d, pg_sides.get(key), OTR_SCALE)
    if abs(d) >= OTR_THRESHOLD and (lo > 0 or hi < 0) and agrees(same, n):
        return "+" if d > 0 else "-"
    return "0"


def human_verdict(key):
    lo, hi = hci[key]
    return "+" if lo > 0 else "-" if hi < 0 else "0"


rows_out, table = [], defaultdict(int)
for s, fname, fkey, q in CONTRASTS:
    key = (s, fname, q)
    pv, hv = panel_verdict(key), human_verdict(key)
    if pv != "0" and hv == pv:
        cls = "hit"
    elif pv != "0" and hv == "0":
        cls = "false positive"
    elif pv != "0":
        cls = "sign error"
    elif hv != "0" and abs(hg[key]) >= OTR_THRESHOLD:
        cls = "miss (human gap at or above threshold)"
    elif hv != "0":
        cls = "miss (human gap below threshold)"
    else:
        cls = "correct null"
    table[cls] += 1
    rows_out.append({"scenario": s, "factor": fname, "question": q, "human_gap": r3(hg[key]), "human_ci": [r3(v) for v in hci[key]],
                     "panel_gap": r3(pg[key]), "panel_ci": [r3(v) for v in pci[key]],
                     "panel_per_model": {m: r3(v) for m, v in pg_per[key].items()},
                     "panel_verdict": pv, "human_verdict": hv, "class": cls,
                     **({"abstaining": [m for m, sd in pg_sides.get(key, {}).items() if at_bound(sd[0], sd[1], OTR_SCALE)]} if ABSTAIN else {})})


def otr_agreement(keys, per_model=None):
    if per_model:
        panel = [pg_per[k][per_model] for k in keys]
    else:
        panel = [pg[k] for k in keys]
    return agreement(panel, [hg[k] for k in keys], [human_verdict(k) != "0" for k in keys])


# does the panel's own 95% interval contain people's gap? A calibrated panel would, about 95% of the time
# (less, since people's gap is itself estimated with noise).
otr_cover = {"panel_interval_contains_human_gap": sum(1 for r in rows_out if r["panel_ci"][0] <= r["human_gap"] <= r["panel_ci"][1]),
             "intervals_overlap": sum(1 for r in rows_out if r["panel_ci"][0] <= r["human_ci"][1] and r["human_ci"][0] <= r["panel_ci"][1]),
             "of": len(rows_out),
             "mean_panel_interval_width": r3(mean([r["panel_ci"][1] - r["panel_ci"][0] for r in rows_out])),
             "mean_human_interval_width": r3(mean([r["human_ci"][1] - r["human_ci"][0] for r in rows_out]))}
all_keys = [(s, f, q) for s, f, _, q in CONTRASTS]
otr = {"n_human_workers": len(workers), "n_human_ratings": len(H),
       "human_workers_matching_their_batch": sum(worker_match.values()),
       "n_panel_ratings": len(P_otr), "threshold_on_1_to_5_scale": round(OTR_THRESHOLD, 3),
       "verdict_table": dict(table), "interval_coverage": otr_cover, "contrasts": rows_out,
       "agreement": {"all": otr_agreement(all_keys)}}
for q in QUESTIONS:
    otr["agreement"][q] = otr_agreement([k for k in all_keys if k[2] == q])
for fname, _ in FACTORS:
    otr["agreement"][fname] = otr_agreement([k for k in all_keys if k[1] == fname])
otr["agreement_per_model"] = {m: otr_agreement(all_keys, m) for m in MODELS}
n_pos = sum(1 for r in rows_out if r["panel_verdict"] != "0")
n_hnull = sum(1 for r in rows_out if r["human_verdict"] == "0")
fp = [r for r in rows_out if r["class"] == "false positive"]
otr["false_positives"] = {"n": len(fp), "mean_abs_panel_gap": r3(mean([abs(r["panel_gap"]) for r in fp])) if fp else None,
                          "mean_abs_human_gap": r3(mean([abs(r["human_gap"]) for r in fp])) if fp else None,
                          "human_gap_same_sign_as_panel": sum(1 for r in fp if r["human_gap"] * r["panel_gap"] > 0),
                          "by_factor": {f: sum(1 for r in fp if r["factor"] == f) for f, _ in FACTORS}}
otr["verdicts_by_factor"] = {f: {q: dict(sorted(defaultdict(int, {c: sum(1 for r in rows_out if r["factor"] == f and r["question"] == q and r["class"] == c)
                                                               for c in {r["class"] for r in rows_out}}).items()))
                                 for q in QUESTIONS} for f, _ in FACTORS}
# Candidate replacements for the confirmed-gap rule, scored against the human verdicts. Indicative only:
# tuned on these 60 contrasts, so a rule that looks best here needs checking on fresh human data.
def rule_outcomes(verdict_fn):
    c = defaultdict(int)
    for s_, f_, _, q_ in CONTRASTS:
        k = (s_, f_, q_)
        pv, hv = verdict_fn(k), human_verdict(k)
        c["confirmed"] += pv != "0"
        c["backed_by_humans"] += pv != "0" and pv == hv
        c["false_positive"] += pv != "0" and hv == "0"
        c["sign_error"] += pv != "0" and hv not in ("0", pv)
        c["human_gaps_found"] += hv != "0" and pv == hv
    c["human_gaps"] = sum(1 for s_, f_, _, q_ in CONTRASTS if human_verdict((s_, f_, q_)) != "0")
    c["human_nulls"] = len(CONTRASTS) - c["human_gaps"]
    return dict(c)


def threshold_rule(t, ci=True, agree=None):
    def v(k):
        d = pg[k]
        lo, hi = pci[k]
        same, n = votes(pg_per[k], d, pg_sides.get(k), OTR_SCALE) if agree is None else (sum(1 for x in pg_per[k].values() if x * d > 0), len(pg_per[k]))
        ok = abs(d) >= t and (not ci or lo > 0 or hi < 0) and (agrees(same, n) if agree is None else same / n >= agree)
        return ("+" if d > 0 else "-") if ok else "0"
    return v


def human_noise_rule(sd, t):
    """Interval built as if the panel's ratings had the spread people show (sd), with the panel's n."""
    def v(k):
        s_, f_, q_ = k
        fkey = dict(FACTORS)[f_]
        na = sum(len(cells[(s_, fkey, 1, q_, m)]) for m in MODELS)
        nb = sum(len(cells[(s_, fkey, 0, q_, m)]) for m in MODELS)
        half = 1.96 * sd * math.sqrt(1 / na + 1 / nb)
        d = pg[k]
        same, n = votes(pg_per[k], d, pg_sides.get(k), OTR_SCALE)
        return ("+" if d > 0 else "-") if abs(d) >= t and abs(d) > half and agrees(same, n) else "0"
    return v


human_sd = mean([otr_levels_sd for otr_levels_sd in [statistics.pstdev([x[q] for x in H]) for q in QUESTIONS]])
otr["rule_variants"] = {
    "benchmark rule (threshold 0.33 on 1-5 = 0.5 on 1-7)": rule_outcomes(threshold_rule(OTR_THRESHOLD)),
    "threshold 0.67 on 1-5 (= 1.0 on 1-7)": rule_outcomes(threshold_rule(2 * OTR_THRESHOLD)),
    "threshold 1.0 on 1-5 (= 1.5 on 1-7)": rule_outcomes(threshold_rule(3 * OTR_THRESHOLD)),
    "interval with human-sized spread (sd %.2f), threshold 0.33" % human_sd: rule_outcomes(human_noise_rule(human_sd, OTR_THRESHOLD)),
    "all panel groups agree, threshold 0.33": rule_outcomes(threshold_rule(OTR_THRESHOLD, agree=1.0)),
}
otr["rates"] = {"panel_confirmed": n_pos,
                "share_of_confirmed_that_humans_back": r3(table["hit"] / n_pos) if n_pos else None,
                "false_positive_rate_among_human_nulls": r3(table["false positive"] / n_hnull) if n_hnull else None,
                "human_nulls": n_hnull,
                "sign_errors": table["sign error"],
                "share_of_human_gaps_the_panel_confirms": r3(table["hit"] / sum(1 for r in rows_out if r["human_verdict"] != "0"))}

# main effects (mean over scenarios of the scenario gaps)
def main_effects(g):
    return {(f, q): mean([g[(s, f, q)] for s in SCEN if (s, f, q) in g]) for f, _ in FACTORS for q in QUESTIONS}


h_me, p_me = main_effects(hg), main_effects(pg)
pm_me = {m: main_effects({k: v[m] for k, v in pg_per.items() if m in v}) for m in MODELS}
hb, pb = defaultdict(list), defaultdict(list)
judges_by_model = {m: sorted({x["judge"] for x in P_otr if x["model"] == m}) for m in MODELS}
for _ in range(args.boot):
    for k, v in main_effects(human_gaps(H, cluster_weights(workers, rng))).items():
        hb[k].append(v)
    jw = {}
    for m in MODELS:
        jw.update(cluster_weights(judges_by_model[m], rng))
    for k, v in main_effects(panel_gaps(P_otr, jw)[0]).items():
        pb[k].append(v)
otr["main_effects"] = [{"factor": f, "question": q, "human": r3(h_me[(f, q)]),
                        "human_ci": [r3(pct(hb[(f, q)], 0.025)), r3(pct(hb[(f, q)], 0.975))],
                        "panel": r3(p_me[(f, q)]), "panel_ci": [r3(pct(pb[(f, q)], 0.025)), r3(pct(pb[(f, q)], 0.975))],
                        "per_model": {m: r3(pm_me[m][(f, q)]) for m in MODELS}} for f, _ in FACTORS for q in QUESTIONS]

# levels and spread: overall means and the within-condition SD of ratings
def level_stats(rows, group_key):
    out = {}
    for q in QUESTIONS:
        by = defaultdict(list)
        for x in rows:
            by[(x["s"], x["cs"], x["ev"], x["ac"]) + ((x["model"],) if group_key else ())].append(x[q])
        sds = [statistics.pstdev(v) for v in by.values() if len(v) >= 2]
        out[q] = {"mean": r3(mean([x[q] for x in rows])), "within_cell_sd": r3(mean(sds)) if sds else None}
    return out


def cell_means(rows):
    by = defaultdict(list)
    for x in rows:
        for q in QUESTIONS:
            by[(x["s"], x["cs"], x["ev"], x["ac"], q)].append(x[q])
    return {k: mean(v) for k, v in by.items()}


hc, pc = cell_means(H), cell_means(P_otr)
otr["cell_level_means"] = {q: {"n": sum(1 for k in hc if k[-1] == q),
                               "pearson_r": r3(pearson([hc[k] for k in hc if k[-1] == q], [pc[k] for k in hc if k[-1] == q]))}
                           for q in QUESTIONS}
otr["levels"] = {"human": level_stats(H, False), "panel": level_stats(P_otr, False),
                 "panel_within_model": level_stats(P_otr, True)}

# sensitivity: humans' first exposure to each scenario only; workers whose rows match their batch only
for label, sub in (("human_first_exposure_only", [x for x in H if x["first_exposure"]]),
                   ("human_rows_matching_batch_only", [x for x in H if x["matches_batch"]])):
    g = human_gaps(sub)
    keys = [k for k in all_keys if k in g]
    otr.setdefault("sensitivity", {})[label] = {
        "n_ratings": len(sub),
        "pearson_r_with_full_human": r3(pearson([g[k] for k in keys], [hg[k] for k in keys])),
        "pearson_r_with_panel": r3(pearson([g[k] for k in keys], [pg[k] for k in keys])),
        "main_effects": {"%s/%s" % fq: r3(v) for fq, v in main_effects(g).items()}}

# reliability by random split halves (humans: workers; panel: judges inside each model)
def split_half(make_halves, gap_fn, keys):
    rs = []
    for _ in range(args.splits):
        h1, h2 = make_halves()
        g1, g2 = gap_fn(h1), gap_fn(h2)
        ks = [k for k in keys if k in g1 and k in g2]
        if len(ks) > 3:
            rs.append(pearson([g1[k] for k in ks], [g2[k] for k in ks]))
    r = mean(rs)
    return {"half_r": r3(r), "spearman_brown": r3(2 * r / (1 + r)) if r > -1 else None}


def human_halves():
    w = workers[:]
    rng.shuffle(w)
    a = set(w[:len(w) // 2])
    return {x: 1 for x in a}, {x: 1 for x in w if x not in a}


def panel_halves():
    h1, h2 = {}, {}
    for m in MODELS:
        j = judges_by_model[m][:]
        rng.shuffle(j)
        for x in j[:len(j) // 2]:
            h1[x] = 1
        for x in j[len(j) // 2:]:
            h2[x] = 1
    return h1, h2


rel = {}
for label, keys in (("all", all_keys),) + tuple((q, [k for k in all_keys if k[2] == q]) for q in QUESTIONS):
    rh = split_half(human_halves, lambda w: human_gaps(H, w), keys)
    rp = split_half(panel_halves, lambda w: panel_gaps(P_otr, w)[0], keys)
    raw = otr["agreement"][label]["pearson_r"]
    dis = raw / math.sqrt(rh["spearman_brown"] * rp["spearman_brown"]) if rh["spearman_brown"] and rp["spearman_brown"] and rh["spearman_brown"] > 0 and rp["spearman_brown"] > 0 else None
    rel[label] = {"human": rh, "panel": rp, "raw_r": raw, "disattenuated_r": r3(dis)}
otr["reliability"] = rel

# ------------------------------------------------------------------ MoCa
moca_h, moca_meta = {}, {}
for tag, name in (("c", "causal_dataset_v1.json"), ("m", "moral_dataset_v1.json")):
    for i, s in enumerate(json.load(open(os.path.join(args.moca, "data", name), encoding="utf-8"))):
        it = json.loads(s)
        dist = json.loads(it["answer_dist"]) if isinstance(it["answer_dist"], str) else it["answer_dist"]
        moca_h["%s%03d" % (tag, i)] = float(dist[0])
        ann = it.get("annotated_sentences") or []
        ann = ast.literal_eval(ann) if isinstance(ann, str) else ann
        fl = defaultdict(set)
        for a in ann:
            if a.get("annotation"):
                fl[a["annotation"][0]].add(a["annotation"][1])
        moca_meta["%s%03d" % (tag, i)] = {"label": it.get("answer"), "factors": {k: sorted(v) for k, v in fl.items()}}
NH = 25
ans = defaultdict(list)
for x in P_moca:
    ans[(x["story"], x["model"])].append(x["yes"])


def moca_panel_share(story, model, sample=None):
    v = ans.get((story, model))
    if not v:
        return None
    if sample:
        v = sample.choices(v, k=len(v))
    return mean(v)


def moca_pair_gap(a, b, sample=None, judges=None):
    vals = {}
    for m in MODELS:
        if judges is not None:
            va = [x["yes"] for x in P_moca if x["model"] == m and x["story"] == a and x["judge"] in judges]
            vb = [x["yes"] for x in P_moca if x["model"] == m and x["story"] == b and x["judge"] in judges]
            if va and vb:
                vals[m] = mean(va) - mean(vb)
            continue
        pa, pb_ = moca_panel_share(a, m, sample), moca_panel_share(b, m, sample)
        if pa is not None and pb_ is not None:
            vals[m] = pa - pb_
    return (mean(list(vals.values())) if vals else None), vals


pairs = [tuple(p) for p in man["moca_pairs"]]
moca_rows = []
for a, b in pairs:
    g, per = moca_pair_gap(a, b)
    hgap = moca_h[a] - moca_h[b]
    se = math.sqrt(moca_h[a] * (1 - moca_h[a]) / NH + moca_h[b] * (1 - moca_h[b]) / NH)
    boots = sorted(moca_pair_gap(a, b, rng)[0] for _ in range(args.boot))
    lo, hi = pct(boots, 0.025), pct(boots, 0.975)
    sides = {m: (moca_panel_share(a, m), moca_panel_share(b, m)) for m in per}
    same, n = votes(per, g, sides, MOCA_SCALE)
    pv = ("+" if g > 0 else "-") if abs(g) >= MOCA_THRESHOLD and (lo > 0 or hi < 0) and per and agrees(same, n) else "0"
    hv = "0" if abs(hgap) < 1.96 * se or se == 0 and hgap == 0 else ("+" if hgap > 0 else "-")
    if se == 0 and hgap != 0:
        hv = "+" if hgap > 0 else "-"
    moca_rows.append({"a": a, "b": b, "human_yes": [r3(moca_h[a]), r3(moca_h[b])], "human_gap": r3(hgap), "human_se": r3(se),
                      "panel_yes": [r3(mean([moca_panel_share(a, m) for m in MODELS if (a, m) in ans])),
                                    r3(mean([moca_panel_share(b, m) for m in MODELS if (b, m) in ans]))],
                      "panel_gap": r3(g), "panel_ci": [r3(lo), r3(hi)], "panel_per_model": {m: r3(v) for m, v in per.items()},
                      "panel_n": {m: [len(ans.get((a, m), [])), len(ans.get((b, m), []))] for m in MODELS},
                      "panel_verdict": pv, "human_verdict": hv,
                      **({"abstaining": [m for m, sd in sides.items() if sd[0] is not None and sd[1] is not None and at_bound(sd[0], sd[1], MOCA_SCALE)]} if ABSTAIN else {})})

moca_cover = {"panel_interval_contains_human_gap": sum(1 for r in moca_rows if r["panel_ci"][0] <= r["human_gap"] <= r["panel_ci"][1]),
              "of": len(moca_rows), "mean_panel_interval_width": r3(mean([r["panel_ci"][1] - r["panel_ci"][0] for r in moca_rows]))}
mtab = defaultdict(int)
for r in moca_rows:
    pv, hv = r["panel_verdict"], r["human_verdict"]
    cls = ("hit" if hv == pv else "false positive" if hv == "0" else "sign error") if pv != "0" else ("miss" if hv != "0" else "correct null")
    r["class"] = cls
    mtab[cls] += 1
mp = [r["panel_gap"] for r in moca_rows]
mh = [r["human_gap"] for r in moca_rows]
moca = {"n_pairs": len(moca_rows), "n_panel_answers": len(P_moca), "verdict_table": dict(mtab), "interval_coverage": moca_cover, "pairs": moca_rows,
        "agreement": agreement(mp, mh, [abs(h) >= HUMAN_CLEAR for h in mh]),
        "agreement_human_significant": agreement(mp, mh, [r["human_verdict"] != "0" for r in moca_rows]),
        "agreement_per_model": {}}
for m in MODELS:
    sub = [r for r in moca_rows if m in r["panel_per_model"]]
    moca["agreement_per_model"][m] = agreement([r["panel_per_model"][m] for r in sub], [r["human_gap"] for r in sub],
                                               [abs(r["human_gap"]) >= HUMAN_CLEAR for r in sub])
# which annotated factor differs between the two stories of a pair (MoCa's own sentence annotations)
for r in moca_rows:
    fa, fb = moca_meta[r["a"]]["factors"], moca_meta[r["b"]]["factors"]
    r["differing_factors"] = sorted(f for f in set(fa) | set(fb) if fa.get(f) != fb.get(f))
by_factor = defaultdict(list)
for r in moca_rows:
    for f in r["differing_factors"] or ["(no annotated difference)"]:
        by_factor[f].append(r)
moca["by_differing_factor"] = {}
for f, rs_ in sorted(by_factor.items(), key=lambda kv: -len(kv[1])):
    clear = [r for r in rs_ if abs(r["human_gap"]) >= HUMAN_CLEAR]
    moca["by_differing_factor"][f] = {
        "pairs": len(rs_), "human_clear": len(clear),
        "mean_abs_gap_human": r3(mean([abs(r["human_gap"]) for r in rs_])),
        "mean_abs_gap_panel": r3(mean([abs(r["panel_gap"]) for r in rs_])),
        "pearson_r": r3(pearson([r["panel_gap"] for r in rs_], [r["human_gap"] for r in rs_])) if len(rs_) > 3 else None,
        "where_human_clear": {"same_sign": sum(1 for r in clear if r["panel_gap"] * r["human_gap"] > 0),
                              "panel_zero": sum(1 for r in clear if r["panel_gap"] == 0),
                              "opposite": sum(1 for r in clear if r["panel_gap"] * r["human_gap"] < 0)}}
n_hnull = sum(1 for r in moca_rows if r["human_verdict"] == "0")
moca["rates"] = {"panel_confirmed": sum(1 for r in moca_rows if r["panel_verdict"] != "0"),
                 "false_positive_rate_among_human_nulls": r3(mtab["false positive"] / n_hnull) if n_hnull else None,
                 "human_nulls": n_hnull, "sign_errors": mtab["sign error"]}
# reliability: humans from binomial sampling error; panel by random split halves of judges
var_h = statistics.pvariance(mh)
rel_h = 1 - mean([r["human_se"] ** 2 for r in moca_rows]) / var_h
rs = []
for _ in range(args.splits):
    h1, h2 = panel_halves()
    g1 = [moca_pair_gap(a, b, judges=set(h1))[0] for a, b in pairs]
    g2 = [moca_pair_gap(a, b, judges=set(h2))[0] for a, b in pairs]
    ok = [(x, y) for x, y in zip(g1, g2) if x is not None and y is not None]
    rs.append(pearson([x for x, _ in ok], [y for _, y in ok]))
rp_half = mean(rs)
rel_p = 2 * rp_half / (1 + rp_half)
moca["reliability"] = {"human_from_sampling_error": r3(rel_h), "panel_half_r": r3(rp_half), "panel_spearman_brown": r3(rel_p),
                       "raw_r": moca["agreement"]["pearson_r"],
                       "disattenuated_r": r3(moca["agreement"]["pearson_r"] / math.sqrt(rel_h * rel_p)) if rel_h > 0 and rel_p > 0 else None}
# story level: panel yes-share against human yes-share, and majority agreement
stories_used = sorted({x["story"] for x in P_moca})
sp = [mean([moca_panel_share(s, m) for m in MODELS if (s, m) in ans]) for s in stories_used]
sh = [moca_h[s] for s in stories_used]
moca["story_level"] = {"n": len(stories_used), "pearson_r": r3(pearson(sp, sh)),
                       "majority_agreement": r3(mean([1.0 if (p > 0.5) == (h > 0.5) else 0.0 for p, h in zip(sp, sh) if p != 0.5 and h != 0.5])),
                       "mean_yes_panel": r3(mean(sp)), "mean_yes_human": r3(mean(sh))}
moca["story_level_per_model"] = {}
for m in MODELS:
    ss = [s for s in stories_used if (s, m) in ans]
    p_ = [moca_panel_share(s, m) for s in ss]
    moca["story_level_per_model"][m] = {"n": len(ss), "pearson_r": r3(pearson(p_, [moca_h[s] for s in ss])),
                                        "majority_agreement": r3(mean([1.0 if (p > 0.5) == (moca_h[s] > 0.5) else 0.0
                                                                       for p, s in zip(p_, ss) if p != 0.5 and moca_h[s] != 0.5]))}

# ------------------------------------------------------------------ recognition
recog = None
if args.recognition and args.recognition_key:
    key = json.load(open(args.recognition_key))
    RIGHT = {"otr": re.compile(r"off\s*the\s*rails|fr[aä]nken", re.I),
             "moca": re.compile(r"\bmoca\b|big[\s-]*bench|causal[_ ]judg", re.I)}
    SPECIFIC = re.compile(r"\b(19|20)\d\d\b|off\s*the\s*rails|\bmoca\b|big[\s-]*bench|causal[_ ]judg", re.I)
    recog = {"items": len(key), "per_model": {}}
    rec_by = {}
    for m in MODELS:
        f = os.path.join(args.recognition, m + ".json")
        if not os.path.exists(f):
            continue
        a = {int(x["item"]): x for x in json.load(open(f))["answers"]}
        rec_by[m] = {}
        per = defaultdict(lambda: {"n": 0, "recognised": 0, "names_a_specific_source": 0, "names_the_dataset": 0})
        for i, (ds, iid) in enumerate(key, 1):
            x = a.get(i, {})
            yes = str(x.get("recognised", "")).lower() == "yes"
            rec_by[m][(ds, str(iid))] = yes
            per[ds]["n"] += 1
            per[ds]["recognised"] += yes
            per[ds]["names_the_dataset"] += bool(yes and RIGHT[ds].search(x.get("source", "")))
            per[ds]["names_a_specific_source"] += bool(yes and SPECIFIC.search(x.get("source", "")))
        recog["per_model"][m] = dict(per)
    # does agreement differ between pairs the model says it recognises and pairs it does not?
    split = {}
    for m, rb in rec_by.items():
        grp = defaultdict(list)
        for r in moca_rows:
            if m not in r["panel_per_model"] or abs(r["human_gap"]) < HUMAN_CLEAR:
                continue
            ra, rb_ = rb.get(("moca", r["a"])), rb.get(("moca", r["b"]))
            if ra is None or rb_ is None:
                continue
            grp["both recognised" if ra and rb_ else "neither recognised" if not ra and not rb_ else "one recognised"].append(
                1.0 if r["panel_per_model"][m] * r["human_gap"] > 0 else 0.0)
        split[m] = {k: {"n": len(v), "sign_agreement": r3(mean(v))} for k, v in grp.items()}
    recog["moca_sign_agreement_by_recognition"] = split

# ------------------------------------------------------------------ each group on its own, corrected for its own noise
# Groups differ in how many judges they have (10 per Claude model, 40 per extra group), so raw correlations
# with people are not comparable across groups; these are divided by sqrt(group reliability x human reliability).
per_group = {}
rel_h_otr = rel["all"]["human"]["spearman_brown"]
for m in MODELS:
    js = judges_by_model[m]
    rows_m = [x for x in P_otr if x["model"] == m]
    rs_o, rs_m = [], []
    for _ in range(args.splits):
        j = js[:]
        rng.shuffle(j)
        h1, h2 = set(j[:len(j) // 2]), set(j[len(j) // 2:])
        g1 = gaps_from(side_means(rows_m, {x: 1 for x in h1}))
        g2 = gaps_from(side_means(rows_m, {x: 1 for x in h2}))
        ks = [k for k in all_keys if k in g1 and k in g2]
        if len(ks) > 3:
            rs_o.append(pearson([g1[k] for k in ks], [g2[k] for k in ks]))
        v1 = [moca_pair_gap(a, b, judges=h1)[1].get(m) for a, b in pairs]
        v2 = [moca_pair_gap(a, b, judges=h2)[1].get(m) for a, b in pairs]
        ok = [(x, y) for x, y in zip(v1, v2) if x is not None and y is not None]
        if len(ok) > 3:
            rs_m.append(pearson([x for x, _ in ok], [y for _, y in ok]))
    ro, rm = mean(rs_o), mean([r for r in rs_m if not math.isnan(r)])
    sb_o, sb_m = 2 * ro / (1 + ro), 2 * rm / (1 + rm)
    raw_o, raw_m = otr["agreement_per_model"][m]["pearson_r"], moca["agreement_per_model"][m]["pearson_r"]
    per_group[m] = {"judges": len(js),
                    "otr": {"raw_r": raw_o, "group_reliability": r3(sb_o),
                            "corrected_r": r3(raw_o / math.sqrt(sb_o * rel_h_otr)) if sb_o > 0 else None},
                    "moca": {"raw_r": raw_m, "group_reliability": r3(sb_m),
                             "corrected_r": r3(raw_m / math.sqrt(sb_m * rel_h)) if sb_m > 0 else None}}

out = {"panel": MODELS, "per_group_corrected": per_group, "excluded_batches": excluded, "otr": otr, "moca": moca, "recognition": recog,
       "settings": {"boot": args.boot, "splits": args.splits, "seed": args.seed, "otr_threshold": OTR_THRESHOLD,
                    "moca_threshold": MOCA_THRESHOLD, "moca_human_clear": HUMAN_CLEAR,
                    **({"agreement_rule": args.agreement_rule} if args.agreement_rule != "three_quarters" else {})}}

# ------------------------------------------------------------------ print
print("OffTheRails: %d human ratings from %d workers (%d match their batch file); %d panel ratings" % (
    len(H), len(workers), sum(worker_match.values()), len(P_otr)))
print("  main effects (gap in scale points, 1-5; positive = first level rated higher):")
for e in otr["main_effects"]:
    print("    %-28s %-15s human %+.2f [%+.2f,%+.2f]  panel %+.2f [%+.2f,%+.2f]  %s" % (
        e["factor"], e["question"], e["human"], *e["human_ci"], e["panel"], *e["panel_ci"],
        " ".join("%s %+.2f" % (m, v) for m, v in e["per_model"].items())))
print("  60 scenario contrasts:", dict(table))
print("  interval coverage:", json.dumps(otr_cover))
print("  false positives:", json.dumps(otr["false_positives"]))
print("  verdicts by factor:", json.dumps(otr["verdicts_by_factor"]))
print("  cell-level means:", json.dumps(otr["cell_level_means"]))
for k, v in otr["rule_variants"].items():
    print("  rule: %-62s %s" % (k, json.dumps(v)))
print("  agreement:", json.dumps(otr["agreement"]["all"]))
for q in QUESTIONS:
    print("   ", q, json.dumps(otr["agreement"][q]))
print("  rates:", json.dumps(otr["rates"]))
print("  reliability:", json.dumps(rel))
print("  levels:", json.dumps(otr["levels"]))
print("  sensitivity:", json.dumps(otr["sensitivity"]))
for m in MODELS:
    print("  per model %-22s" % m, json.dumps(otr["agreement_per_model"][m]))
print("MoCa: %d pairs, %d panel answers" % (len(moca_rows), len(P_moca)))
print("  verdicts:", dict(mtab), json.dumps(moca["rates"]))
print("  interval coverage:", json.dumps(moca_cover))
print("  agreement:", json.dumps(moca["agreement"]))
print("  reliability:", json.dumps(moca["reliability"]))
print("  story level:", json.dumps(moca["story_level"]))
for f, v in moca["by_differing_factor"].items():
    print("  differs in %-24s" % f, json.dumps(v))
for m in MODELS:
    print("  per model %-22s" % m, json.dumps(moca["agreement_per_model"][m]), json.dumps(moca["story_level_per_model"][m]))
if recog:
    print("Recognition:", json.dumps(recog["per_model"]))
    print("  MoCa sign agreement by recognition:", json.dumps(recog["moca_sign_agreement_by_recognition"]))
print("Each group alone, corrected for its own noise:")
for m, v in per_group.items():
    print("  %-22s judges %2d  OTR r %s (reliability %s, corrected %s)  MoCa r %s (reliability %s, corrected %s)" % (
        m, v["judges"], v["otr"]["raw_r"], v["otr"]["group_reliability"], v["otr"]["corrected_r"],
        v["moca"]["raw_r"], v["moca"]["group_reliability"], v["moca"]["corrected_r"]))
if excluded:
    print("excluded batches:", excluded)
if args.out:
    json.dump(out, open(args.out, "w"), indent=1)
