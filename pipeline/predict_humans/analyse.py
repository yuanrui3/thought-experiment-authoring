#!/usr/bin/env python3
"""Score author models' predictions of human results against what people actually answered.

    python3 pipeline/predict_humans/analyse.py --predictions DIR --moral-evals DIR [--out FILE]

Predictions: {model}_otr_r{n}.json and {model}_moca_r{n}.json, as written by the prediction runs
(see build.py). Human results and the model panels' measured gaps come from the calibration outputs
(reports/calibration_numbers.json and reports/calibration_numbers_other_panels.json), so every
predictor is scored on exactly the same 60 OffTheRails contrasts and 85 MoCa pairs.

Predictors compared:
  each author model (its runs averaged);
  "no difference": predicts a zero gap everywhere;
  the Claude panel, Gemini 4 Argon, Gemini 3 Flash: their measured gaps used as predictions.

OffTheRails scoring uses the pilot's prediction score (direction half, size half; opposite = 0), with
the pilot's 0.5 / 1.5 thresholds on the 1-7 scale rescaled to 1-5 (0.33 / 1.0). People's result for a
contrast is "no difference" below 0.33, a direction when its 95% interval excludes zero, otherwise unclear.
"""
import argparse, csv, glob, json, math, os, re, statistics, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import score as S  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--predictions", required=True)
ap.add_argument("--moral-evals", help="clone of cicl-stanford/moral-evals, for people's mean rating per version")
ap.add_argument("--manifest", default=os.path.join(HERE, "manifest.json"))
ap.add_argument("--calibration", default=os.path.join(ROOT, "reports", "calibration_numbers.json"))
ap.add_argument("--other-panels", default=os.path.join(ROOT, "reports", "calibration_numbers_other_panels.json"))
ap.add_argument("--out")
args = ap.parse_args()

man = json.load(open(args.manifest))
cal = json.load(open(args.calibration))
oth = json.load(open(args.other_panels))
NONE, LARGE = 0.5 * 4 / 6, 1.5 * 4 / 6
FACTORS = {"means_minus_side_effect": "cs", "evitable_minus_inevitable": "ev", "action_minus_omission": "ac"}
CLEAR = 0.30


def mean(x):
    return sum(x) / len(x)


def pearson(x, y):
    if len(x) < 3 or statistics.pstdev(x) == 0 or statistics.pstdev(y) == 0:
        return None
    mx, my = mean(x), mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) * statistics.pstdev(x) * statistics.pstdev(y))


def r3(v):
    return None if v is None else round(v, 3)


def factors_of(cond):
    return {"cs": 1 if cond.startswith("cc_") else 0, "ev": 1 if "_evitable_" in cond else 0, "ac": 1 if cond.endswith("action_yes") else 0}


# ------------------------------------------------------------------ predictions
files = sorted(glob.glob(os.path.join(args.predictions, "*_r*.json")))
P_otr, P_moca, problems = defaultdict(dict), defaultdict(dict), []
for f in files:
    m = re.match(r"(.+)_(otr|moca)_r(\d+)\.json$", os.path.basename(f))
    if not m:
        continue
    model, ds, run = m.group(1), m.group(2), m.group(3)
    try:
        a = json.load(open(f))
    except Exception as e:
        problems.append("%s: unreadable (%s)" % (os.path.basename(f), e))
        continue
    rm = man["runs"][run][ds]
    if ds == "otr":
        cells = {}
        for sc in a["scenarios"]:
            info = rm[str(sc["scenario"])]
            for v in sc["versions"]:
                cond = info["versions"][str(v["version"])]
                cells[(info["scenario_id"], cond)] = (float(v["statement1"]), float(v["statement2"]))
        if len(cells) != 80:
            problems.append("%s: %d of 80 versions" % (os.path.basename(f), len(cells)))
        P_otr[model][run] = cells
    else:
        st = {rm[str(x["story"])]: float(x["yes_percent"]) / 100 for x in a["stories"] if str(x["story"]) in rm}
        if len(st) != len(rm):
            problems.append("%s: %d of %d stories" % (os.path.basename(f), len(st), len(rm)))
        P_moca[model][run] = st

# ------------------------------------------------------------------ OffTheRails: contrasts from predicted means
H = {(c["scenario"], c["factor"], c["question"]): c for c in cal["otr"]["contrasts"]}
KEYS = sorted(H)


def contrasts(cells):
    out = {}
    for (s, f, q) in KEYS:
        fk = FACTORS[f]
        qi = 0 if q == "permissibility" else 1
        hi = [v[qi] for (sid, c), v in cells.items() if sid == s and factors_of(c)[fk] == 1]
        lo = [v[qi] for (sid, c), v in cells.items() if sid == s and factors_of(c)[fk] == 0]
        if hi and lo:
            out[(s, f, q)] = mean(hi) - mean(lo)
    return out


def human_obs(k):
    g, (lo, hi) = H[k]["human_gap"], H[k]["human_ci"]
    size = "none" if abs(g) < NONE else ("large" if abs(g) >= LARGE else "small")
    if size == "none":
        d = "none"
    elif lo > 0 or hi < 0:
        d = "A_higher" if g > 0 else "B_higher"
    else:
        d = "unclear"
    return {"direction": d, "size": size}


def pred_class(g):
    size = "none" if abs(g) < NONE else ("large" if abs(g) >= LARGE else "small")
    return {"direction": "none" if size == "none" else ("A_higher" if g > 0 else "B_higher"), "size": size}


def score_otr(pred, keys=None):
    keys = [k for k in (keys or KEYS) if k in pred]
    p, h = [pred[k] for k in keys], [H[k]["human_gap"] for k in keys]
    clear = [(pp, hh) for k, pp, hh in zip(keys, p, h) if H[k]["human_verdict"] != "0"]
    sc = [S.prediction_score(pred_class(pred[k]), human_obs(k), H[k]["human_gap"]) for k in keys]
    return {"n": len(keys), "pearson_r": r3(pearson(p, h)), "mean_abs_error": r3(mean([abs(a - b) for a, b in zip(p, h)])),
            "mean_abs_predicted_gap": r3(mean([abs(a) for a in p])), "mean_abs_human_gap": r3(mean([abs(b) for b in h])),
            "prediction_score": r3(mean([x["score"] for x in sc])), "direction_hits": sum(x["direction_hit"] for x in sc),
            "size_hits": sum(x["size_hit"] for x in sc), "opposite": sum(x["opposite"] for x in sc),
            "same_sign_where_people_show_a_gap": "%d of %d" % (sum(1 for a, b in clear if a * b > 0), len(clear))}


otr_pred = {}
otr_runs = {}
for model, runs in P_otr.items():
    cs = {run: contrasts(cells) for run, cells in runs.items()}
    otr_runs[model] = cs
    otr_pred[model] = {k: mean([c[k] for c in cs.values() if k in c]) for k in KEYS if any(k in c for c in cs.values())}
baselines = {"no difference (always 0)": {k: 0.0 for k in KEYS},
             "Claude panel (measured)": {k: H[k]["panel_gap"] for k in KEYS}}
for label, key in (("Gemini 4 Argon (measured)", "gemini-4-argon alone"), ("Gemini 3 Flash (measured)", "gemini-3-flash-preview alone")):
    baselines[label] = {(c["scenario"], c["factor"], c["question"]): c["panel_gap"] for c in oth[key]["otr"]["contrasts"]}

otr_out = {"predictors": {}, "by_factor": {}, "run_to_run_r": {}}
for name, pred in list(otr_pred.items()) + list(baselines.items()):
    otr_out["predictors"][name] = score_otr(pred)
    otr_out["by_factor"][name] = {f: score_otr(pred, [k for k in KEYS if k[1] == f]) for f in FACTORS}
for model, cs in otr_runs.items():
    if len(cs) >= 2:
        a, b = list(cs.values())[:2]
        ks = [k for k in KEYS if k in a and k in b]
        otr_out["run_to_run_r"][model] = r3(pearson([a[k] for k in ks], [b[k] for k in ks]))
otr_out["human_reliability"] = cal["otr"]["reliability"]["all"]["human"]["spearman_brown"]
otr_out["ceiling_r"] = r3(math.sqrt(otr_out["human_reliability"]))

# people's mean rating per version, against predicted means (levels, not just gaps)
if args.moral_evals:
    path = os.path.join(args.moral_evals, "offtherails", "prolific-exp-2", "data_long_format.csv")
    CODE = ({0: "coc", 1: "cc"}, {0: "inevitable", 1: "evitable"}, {0: "prevention_no", 1: "action_yes"})
    hc = defaultdict(list)
    for r in csv.DictReader(open(path, encoding="utf-8")):
        cond = "%s_%s_%s" % (CODE[0][int(r["causal_structure"])], CODE[1][int(r["evitability"])], CODE[2][int(r["action"])])
        hc[(int(r["scenario_id"]), cond)].append((int(r["permissibility_rating"]), int(r["intention_rating"])))
    hmean = {k: (mean([x[0] for x in v]), mean([x[1] for x in v])) for k, v in hc.items()}
    otr_out["version_means"] = {}
    for model, runs in P_otr.items():
        avg = {k: tuple(mean([runs[r][k][i] for r in runs if k in runs[r]]) for i in (0, 1)) for k in hmean if all(k in runs[r] for r in runs)}
        res = {}
        for i, q in enumerate(("permissibility", "intention")):
            p, h = [avg[k][i] for k in avg], [hmean[k][i] for k in avg]
            res[q] = {"pearson_r": r3(pearson(p, h)), "mean_abs_error": r3(mean([abs(a - b) for a, b in zip(p, h)])),
                      "mean_predicted": r3(mean(p)), "mean_human": r3(mean(h))}
        otr_out["version_means"][model] = res

# ------------------------------------------------------------------ MoCa
pairs = {(r["a"], r["b"]): r for r in cal["moca"]["pairs"]}
human_yes = {}
for (a, b), r in pairs.items():
    human_yes[a], human_yes[b] = r["human_yes"]


def score_moca(gap, keys=None):
    keys = [k for k in (keys or list(pairs)) if k in gap]
    p, h = [gap[k] for k in keys], [pairs[k]["human_gap"] for k in keys]
    clear = [(a, b) for a, b in zip(p, h) if abs(b) >= CLEAR]
    return {"n": len(keys), "pearson_r": r3(pearson(p, h)), "mean_abs_error": r3(mean([abs(a - b) for a, b in zip(p, h)])),
            "mean_abs_predicted_gap": r3(mean([abs(a) for a in p])), "mean_abs_human_gap": r3(mean([abs(b) for b in h])),
            "where_people_differ_by_0.30_or_more": {"n": len(clear), "same_sign": sum(1 for a, b in clear if a * b > 0),
                                                    "no_gap": sum(1 for a, b in clear if a == 0), "opposite": sum(1 for a, b in clear if a * b < 0)}}


moca_pred, moca_story = {}, {}
for model, runs in P_moca.items():
    st = {s: mean([runs[r][s] for r in runs if s in runs[r]]) for s in human_yes if any(s in runs[r] for r in runs)}
    moca_story[model] = st
    moca_pred[model] = {k: st[k[0]] - st[k[1]] for k in pairs if k[0] in st and k[1] in st}
mb = {"no difference (always 0)": {k: 0.0 for k in pairs}, "Claude panel (measured)": {k: r["panel_gap"] for k, r in pairs.items()}}
for label, key in (("Gemini 4 Argon (measured)", "gemini-4-argon alone"), ("Gemini 3 Flash (measured)", "gemini-3-flash-preview alone")):
    mb[label] = {(r["a"], r["b"]): r["panel_gap"] for r in oth[key]["moca"]["pairs"]}
moca_out = {"predictors": {}, "stories": {}, "by_differing_factor": {}, "run_to_run_r": {}}
for name, gap in list(moca_pred.items()) + list(mb.items()):
    moca_out["predictors"][name] = score_moca(gap)
    fac = defaultdict(list)
    for k, r in pairs.items():
        for f in r.get("differing_factors") or ["(no annotated difference)"]:
            fac[f].append(k)
    moca_out["by_differing_factor"][name] = {f: score_moca(gap, ks) for f, ks in fac.items()}
for model, st in moca_story.items():
    ss = sorted(st)
    p, h = [st[s] for s in ss], [human_yes[s] for s in ss]
    moca_out["stories"][model] = {"n": len(ss), "pearson_r": r3(pearson(p, h)), "mean_abs_error": r3(mean([abs(a - b) for a, b in zip(p, h)])),
                                  "majority_agreement": r3(mean([1.0 if (a > 0.5) == (b > 0.5) else 0.0 for a, b in zip(p, h) if a != 0.5 and b != 0.5]))}
    runs = P_moca[model]
    if len(runs) >= 2:
        g = []
        for r in list(runs)[:2]:
            g.append({k: runs[r][k[0]] - runs[r][k[1]] for k in pairs if k[0] in runs[r] and k[1] in runs[r]})
        ks = [k for k in pairs if k in g[0] and k in g[1]]
        moca_out["run_to_run_r"][model] = r3(pearson([g[0][k] for k in ks], [g[1][k] for k in ks]))
moca_out["human_reliability"] = cal["moca"]["reliability"]["human_from_sampling_error"]
moca_out["ceiling_r"] = r3(math.sqrt(moca_out["human_reliability"]))

out = {"authors": sorted(set(P_otr) | set(P_moca)), "runs": {m: sorted(set(P_otr.get(m, {})) | set(P_moca.get(m, {}))) for m in set(P_otr) | set(P_moca)},
       "problems": problems, "otr": otr_out, "moca": moca_out,
       "settings": {"otr_thresholds_1_to_5": [round(NONE, 3), round(LARGE, 3)], "moca_clear_gap": CLEAR}}

# ------------------------------------------------------------------ print
print("authors:", ", ".join("%s (runs %s)" % (m, ",".join(out["runs"][m])) for m in out["authors"]))
if problems:
    print("problems:", "; ".join(problems))
print("\nOffTheRails, 60 contrasts (ceiling r %.2f from people's own reliability)" % otr_out["ceiling_r"])
print("  %-28s %6s %6s %8s %8s %6s %5s %5s %4s %s" % ("predictor", "r", "MAE", "|pred|", "|human|", "score", "dir", "size", "opp", "same sign where people differ"))
for name, v in otr_out["predictors"].items():
    print("  %-28s %6s %6s %8s %8s %6s %5d %5d %4d %s" % (name, v["pearson_r"], v["mean_abs_error"], v["mean_abs_predicted_gap"], v["mean_abs_human_gap"],
                                                         v["prediction_score"], v["direction_hits"], v["size_hits"], v["opposite"], v["same_sign_where_people_show_a_gap"]))
print("  by factor (r / MAE / score):")
for name, fs in otr_out["by_factor"].items():
    print("    %-26s " % name + "  ".join("%s %s/%s/%s" % (f.split("_")[0], v["pearson_r"], v["mean_abs_error"], v["prediction_score"]) for f, v in fs.items()))
print("  run-to-run r:", otr_out["run_to_run_r"])
if "version_means" in otr_out:
    print("  version means:", json.dumps(otr_out["version_means"]))
print("\nMoCa, 85 pairs (ceiling r %.2f)" % moca_out["ceiling_r"])
for name, v in moca_out["predictors"].items():
    w = v["where_people_differ_by_0.30_or_more"]
    print("  %-28s r %6s  MAE %5s  |pred| %5s |human| %5s  where people differ (%d): same %d, none %d, opposite %d" % (
        name, v["pearson_r"], v["mean_abs_error"], v["mean_abs_predicted_gap"], v["mean_abs_human_gap"], w["n"], w["same_sign"], w["no_gap"], w["opposite"]))
for name, fs in moca_out["by_differing_factor"].items():
    print("    %-26s " % name + "  ".join("%s r %s" % (f[:12], v["pearson_r"]) for f, v in fs.items()))
print("  stories:", json.dumps(moca_out["stories"]))
print("  run-to-run r:", moca_out["run_to_run_r"])
if args.out:
    json.dump(out, open(args.out, "w"), indent=1)
