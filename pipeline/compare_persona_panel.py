#!/usr/bin/env python3
"""Compare the pilot's persona panel with the original panel on the same judge models.

    python3 pipeline/compare_persona_panel.py [--new-run persona] [--base-run main] [--boot 10000]

Scores, with score.py's rules and the pilot's audits, into folders under out/:
  out/<new-run>/                the persona panel (whichever judge models it has)
  out/<base-run>_same_models/   the original panel restricted to those same judge models
and reads out/ (the published panel) and out/gemini/ (if present). Writes out/persona_comparison.csv
and out/persona_comparison_summary.json: each pair's verdict under each panel, authors under each,
and the spread of ratings within each model. Finally reruns score.py on the base run, which rebuilds
results.html with a section on the persona panel.
"""
import argparse, csv, json, os, statistics, subprocess, sys, tempfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "out")
ap = argparse.ArgumentParser()
ap.add_argument("--new-run", default="persona")
ap.add_argument("--base-run", default="main")
ap.add_argument("--boot", type=int, default=10000)
args = ap.parse_args()

J = os.path.join(ROOT, "judgments.csv")
with open(J, newline="", encoding="utf-8") as f:
    rd = csv.DictReader(f)
    cols, rows = rd.fieldnames, list(rd)
new_rows = [r for r in rows if r["run_id"] == args.new_run]
models = sorted({r["judge_model"] for r in new_rows})
base_rows = [r for r in rows if r["run_id"] == args.base_run and r["judge_model"] in models]


def score(rows_, run, out):
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8") as tmp:
        w = csv.DictWriter(tmp, fieldnames=cols)
        w.writeheader()
        w.writerows(rows_)
    subprocess.run([sys.executable, os.path.join(ROOT, "score.py"), "--judgments", tmp.name, "--run", run, "--audit-run", args.base_run,
                    "--out", out, "--no-report", "--boot", str(args.boot)], check=True, stdout=subprocess.DEVNULL)
    os.unlink(tmp.name)


same = os.path.join(OUT, "%s_same_models" % args.base_run)
score(new_rows, args.new_run, os.path.join(OUT, args.new_run))
score(base_rows, args.base_run, same)
panels = [("published", OUT), ("original_same_models", same), ("persona", os.path.join(OUT, args.new_run))]
if os.path.exists(os.path.join(OUT, "gemini", "pair_scores.csv")):
    panels.append(("gemini", os.path.join(OUT, "gemini")))
P = {k: {r["pair_id"]: r for r in csv.DictReader(open(os.path.join(d, "pair_scores.csv"), encoding="utf-8"))} for k, d in panels}
A = {k: {r["tier"]: r for r in csv.DictReader(open(os.path.join(d, "author_summary.csv"), encoding="utf-8"))} for k, d in panels}


def verdict(r):
    return "%s/%s" % (r["observed_direction"], r["observed_size"])


out_rows = []
for pid, o in P["original_same_models"].items():
    p = P["persona"][pid]
    rec = {"pair_id": pid, "pair_type": o["pair_type"], "factor_id": o["factor_id"], "author": o["author_tier"],
           "predicted": "%s/%s" % (o["predicted_direction"], o["predicted_size"])}
    for k, _ in panels:
        r = P[k][pid]
        rec.update({k + "_effect": r["effect"], k + "_ci": "[%s, %s]" % (r["ci_low"], r["ci_high"]), k + "_verdict": verdict(r),
                    k + "_models_agreeing": "%s/%s" % (r["groups_same_sign"], r["groups_total"]), k + "_prediction_score": r["prediction_score"],
                    k + "_composite": r["composite"]})
    rec["persona_changes_verdict"] = verdict(o) != verdict(p)
    out_rows.append(rec)
with open(os.path.join(OUT, "persona_comparison.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
    w.writeheader()
    w.writerows(out_rows)


def sd_within(rows_):
    cell = defaultdict(list)
    for r in rows_:
        cell[(r["judge_model"], r["pair_id"], r["version"])].append(int(r["rating"]))
    by = defaultdict(list)
    for (m, _, _), v in cell.items():
        if len(v) >= 2:
            by[m].append(statistics.pstdev(v))
    return {m: round(statistics.mean(v), 3) for m, v in sorted(by.items())}


def pearson(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) * statistics.pstdev(x) * statistics.pstdev(y))


au = [r for r in out_rows if r["pair_type"] == "authored"]
key = {p["pair_id"]: p["comprehension_question"]["correct"] for p in json.load(open(os.path.join(ROOT, "vignettes.json")))["pairs"]}
comp = lambda rows_: round(statistics.mean(1.0 if r["comprehension_answer"] == key[r["pair_id"]][r["version"]] else 0.0 for r in rows_), 3)
summary = {
    "new_run": args.new_run, "judge_models": models, "n_new_ratings": len(new_rows),
    "spread_within_model": {"original": sd_within(base_rows), "persona": sd_within(new_rows)},
    "comprehension": {"original": comp(base_rows), "persona": comp(new_rows)},
    "verdicts_changed": sum(r["persona_changes_verdict"] for r in out_rows),
    "verdicts_changed_authored": sum(r["persona_changes_verdict"] for r in au),
    "effect_correlation_with_original": round(pearson([float(r["original_same_models_effect"]) for r in out_rows],
                                                      [float(r["persona_effect"]) for r in out_rows]), 3),
    "mean_abs_effect_authored": {k: round(statistics.mean(abs(float(r[k + "_effect"])) for r in au), 2) for k, _ in panels},
    "null_controls_with_a_gap": {k: sum(1 for r in out_rows if r["pair_type"] == "control_null" and not r[k + "_verdict"].startswith("none"))
                                 for k, _ in panels},
    "classic_controls_in_expected_direction": {k: sum(1 for r in out_rows if r["pair_type"] == "control_classic"
                                                      and r[k + "_verdict"].split("/")[0] == r["predicted"].split("/")[0]) for k, _ in panels},
    "changed": [{k: r[k] for k in ("pair_id", "predicted", "original_same_models_verdict", "persona_verdict", "original_same_models_prediction_score",
                                     "persona_prediction_score")} for r in out_rows if r["persona_changes_verdict"]],
    "authors": {t: {k: {"mean_composite": A[k][t]["mean_composite"], "mean_prediction_score": A[k][t]["mean_prediction_score"],
                        "full_hits": A[k][t]["full_hits"]} for k, _ in panels} for t in sorted(A["persona"])},
}
if "gemini" in P:
    summary["agrees_with_gemini"] = {k: sum(1 for r in out_rows if r[k + "_verdict"] == r["gemini_verdict"]) for k in ("original_same_models", "persona")}
json.dump(summary, open(os.path.join(OUT, "persona_comparison_summary.json"), "w"), indent=1)

print("persona run %r: %d ratings from judge models %s" % (args.new_run, len(new_rows), ", ".join(models)))
print("rating spread within one model (SD):", json.dumps(summary["spread_within_model"]))
print("comprehension:", summary["comprehension"])
print("verdicts changed by personas: %d of %d (authored %d of %d); effect correlation with original %.2f" % (
    summary["verdicts_changed"], len(out_rows), summary["verdicts_changed_authored"], len(au), summary["effect_correlation_with_original"]))
print("mean |effect| on authored pairs:", summary["mean_abs_effect_authored"])
print("null controls with a gap:", summary["null_controls_with_a_gap"], "| classic controls right way:", summary["classic_controls_in_expected_direction"])
if "agrees_with_gemini" in summary:
    print("verdicts identical to Gemini's:", summary["agrees_with_gemini"])
for c in summary["changed"]:
    print("  %-28s predicted %-14s original %-18s persona %-18s scores %s -> %s" % (c["pair_id"], c["predicted"], c["original_same_models_verdict"],
                                                                                c["persona_verdict"], c["original_same_models_prediction_score"], c["persona_prediction_score"]))
# rebuild the main results page so its persona section shows these numbers
subprocess.run([sys.executable, os.path.join(ROOT, "score.py"), "--run", args.base_run, "--boot", str(args.boot)], check=True, stdout=subprocess.DEVNULL)
print("rebuilt results.html")
print("authors (mean composite / full hits):")
for t, v in summary["authors"].items():
    print("  %-7s " % t + "  ".join("%s %s/%s" % (k, v[k]["mean_composite"], v[k]["full_hits"]) for k, _ in panels))
