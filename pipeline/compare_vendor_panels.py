#!/usr/bin/env python3
"""Score the pilot with each vendor's panel and with the vendors as two judge groups, and compare.

    python3 pipeline/compare_vendor_panels.py [--claude-run main] [--other-run gemini] [--boot 10000]

Runs score.py (same rules, same audits) four ways, each into its own folder under out/:
  out/                       the Claude panel alone (the pilot as published; read, not rewritten)
  out/gemini/                the other vendor's panel alone
  out/vendor_groups/         two judge groups, one per vendor: each vendor's ratings pooled, the effect
                             averaged over the two vendors, and a gap confirmed only if both agree in sign
  out/claude_plus_gemini/    all six models as six equal judge groups
and writes out/vendor_comparison.csv with each pair's verdict under each.
"""
import argparse, csv, json, os, statistics, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--claude-run", default="main")
ap.add_argument("--other-run", default="gemini")
ap.add_argument("--boot", type=int, default=10000)
args = ap.parse_args()
OUT = os.path.join(ROOT, "out")


def score(judgments, run, out):
    subprocess.run([sys.executable, os.path.join(ROOT, "score.py"), "--judgments", judgments, "--run", run, "--audit-run", args.claude_run,
                    "--out", out, "--no-report", "--boot", str(args.boot)], check=True, stdout=subprocess.DEVNULL)


J = os.path.join(ROOT, "judgments.csv")
both = "%s,%s" % (args.claude_run, args.other_run)
score(J, args.other_run, os.path.join(OUT, "gemini"))
score(J, both, os.path.join(OUT, "claude_plus_gemini"))
with open(J, newline="", encoding="utf-8") as f:
    rd = csv.DictReader(f)
    cols, rows = rd.fieldnames, [r for r in rd if r["run_id"] in both.split(",")]
with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="", encoding="utf-8") as tmp:
    w = csv.DictWriter(tmp, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow(dict(r, judge_group=r["judge_vendor"]))
score(tmp.name, both, os.path.join(OUT, "vendor_groups"))
os.unlink(tmp.name)

PANELS = [("claude", OUT), ("gemini", os.path.join(OUT, "gemini")), ("vendor_groups", os.path.join(OUT, "vendor_groups")),
          ("six_models", os.path.join(OUT, "claude_plus_gemini"))]
P = {k: {r["pair_id"]: r for r in csv.DictReader(open(os.path.join(d, "pair_scores.csv"), encoding="utf-8"))} for k, d in PANELS}
A = {k: {r["tier"]: r for r in csv.DictReader(open(os.path.join(d, "author_summary.csv"), encoding="utf-8"))} for k, d in PANELS}
ids = list(P["claude"])


def verdict(r):
    return "%s/%s" % (r["observed_direction"], r["observed_size"])


out_rows = []
for pid in ids:
    c, g, v, s = (P[k][pid] for k in ("claude", "gemini", "vendor_groups", "six_models"))
    rec = {"pair_id": pid, "pair_type": c["pair_type"], "factor_id": c["factor_id"], "author": c["author_tier"],
           "predicted": "%s/%s" % (c["predicted_direction"], c["predicted_size"])}
    for k, r in (("claude", c), ("gemini", g), ("vendor_groups", v), ("six_models", s)):
        rec.update({k + "_effect": r["effect"], k + "_ci": "[%s, %s]" % (r["ci_low"], r["ci_high"]), k + "_verdict": verdict(r),
                    k + "_prediction_score": r["prediction_score"], k + "_composite": r["composite"]})
    rec["vendors_agree"] = verdict(c) == verdict(g)
    rec["vendors_agree_on_direction"] = c["observed_direction"] == g["observed_direction"]
    out_rows.append(rec)
with open(os.path.join(OUT, "vendor_comparison.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0]))
    w.writeheader()
    w.writerows(out_rows)


def pearson(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (len(x) * statistics.pstdev(x) * statistics.pstdev(y))


au = [r for r in out_rows if r["pair_type"] == "authored"]
summary = {"pairs": len(out_rows),
           "verdicts_agree": sum(r["vendors_agree"] for r in out_rows),
           "directions_agree": sum(r["vendors_agree_on_direction"] for r in out_rows),
           "authored_verdicts_agree": sum(r["vendors_agree"] for r in au), "authored": len(au),
           "effect_correlation_all": round(pearson([float(r["claude_effect"]) for r in out_rows], [float(r["gemini_effect"]) for r in out_rows]), 3),
           "effect_correlation_authored": round(pearson([float(r["claude_effect"]) for r in au], [float(r["gemini_effect"]) for r in au]), 3),
           "mean_abs_effect_authored": {k: round(statistics.mean(abs(float(r[k + "_effect"])) for r in au), 2) for k in ("claude", "gemini")},
           "disagreements": [{k: r[k] for k in ("pair_id", "predicted", "claude_verdict", "gemini_verdict", "vendor_groups_verdict",
                                                  "claude_prediction_score", "gemini_prediction_score", "vendor_groups_prediction_score")}
                             for r in out_rows if not r["vendors_agree"]],
           "authors": {t: {k: {"mean_composite": A[k][t]["mean_composite"], "mean_prediction_score": A[k][t]["mean_prediction_score"],
                               "direction_hits": A[k][t]["direction_hits"], "full_hits": A[k][t]["full_hits"]} for k, _ in PANELS}
                       for t in sorted(A["claude"])}}
json.dump(summary, open(os.path.join(OUT, "vendor_comparison_summary.json"), "w"), indent=1)

print("verdicts (direction and size) agree on %d of %d pairs (authored %d of %d); directions agree on %d" % (
    summary["verdicts_agree"], len(out_rows), summary["authored_verdicts_agree"], len(au), summary["directions_agree"]))
print("effect correlation across pairs: all %.2f, authored %.2f; mean |effect| on authored pairs: Claude %.2f, Gemini %.2f" % (
    summary["effect_correlation_all"], summary["effect_correlation_authored"], summary["mean_abs_effect_authored"]["claude"],
    summary["mean_abs_effect_authored"]["gemini"]))
print("pairs where the vendors' verdicts differ:")
for d in summary["disagreements"]:
    print("  %-26s predicted %-14s Claude %-16s Gemini %-16s two-vendor %-16s scores %s / %s / %s" % (
        d["pair_id"], d["predicted"], d["claude_verdict"], d["gemini_verdict"], d["vendor_groups_verdict"],
        d["claude_prediction_score"], d["gemini_prediction_score"], d["vendor_groups_prediction_score"]))
print("authors (mean composite | mean prediction score | full hits of 5):")
for t, v in summary["authors"].items():
    print("  %-7s " % t + "  ".join("%s %s | %s | %s" % (k, v[k]["mean_composite"], v[k]["mean_prediction_score"], v[k]["full_hits"]) for k, _ in PANELS))
print("wrote out/vendor_comparison.csv, out/vendor_comparison_summary.json and out/{gemini,vendor_groups,claude_plus_gemini}/")
