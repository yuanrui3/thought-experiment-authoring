#!/usr/bin/env python3
"""Test of weighting judge models by how well they track people, run before deciding whether to adopt it.

    python3 pipeline/test_judge_weights.py --moral-evals DIR --moca DIR

Requested by the owner on 26 November 2026 ("go ahead with weighting judge models by how well they track people").
This file, with the rule's code in score.py and pipeline/calibration/analyse.py, was committed BEFORE the test was run.
The weights and the criteria below are fixed here.

THE WEIGHTS
  For each judge model, from the public human data, with the panel type it is used in (persona or plain):
      w = max(0, (r_OffTheRails + r_MoCa) / 2)
  r is the raw Pearson correlation between that model's own gaps and the human gaps over the 60 OffTheRails contrasts
  or the 85 MoCa pairs, as pipeline/calibration/analyse.py reports it (agreement_per_model). Raw, not corrected for
  reliability: a noisy model should count for less. A model with a negative average gets weight 0. A model's r does
  not depend on which other models are in the panel.
  Persona weights come from reports/calibration_numbers_persona_noise.json, and plain weights from that file (three
  models) and reports/calibration_numbers.json (four models).

THE RULE ("weighted", in score.py and analyse.py)
  The gap is the weighted mean of the models' gaps, and its 95% interval is the same stratified bootstrap of that
  weighted mean. A gap needs |gap| >= 0.5, an interval excluding 0, and the models agreeing in sign carrying at least
  two thirds of the total weight. A model with weight 0 is left out entirely. At least two models with positive weight
  are needed. With equal weights it is exactly the current two-thirds rule (checked before this commit: byte-identical
  on round 2b pooled and on the persona calibration).

CRITERIA (all three must pass for adoption; otherwise the two-thirds rule stays)
  C1 validity, out of sample. The three-model persona panel on the human data. Weights estimated on MoCa alone
     (max(0, r_MoCa)) score the OffTheRails contrasts, and weights estimated on OffTheRails alone score the MoCa pairs,
     so no verdict is scored with weights fitted to its own data. Together: at least 50% of the confirmed gaps are
     backed by people (pilot rule 55%, two-thirds 39%), and at least 12 of the gaps people show are confirmed (12, 13).
  C2 stability. Round 2b, panel 1 against panel 2, with the persona weights: at most 2 of 27 authored pairs change
     prediction score by more than 0.25 (pilot rule 5, two-thirds 1).
  C3 sanity. No rescored panel confirms more null controls than it does under the current rule.
  If all pass:
    - run Fable's 10 persona calibration judges (batches b31-b40, the same prompt as the other persona judges) to get
      Fable's persona weight;
    - write pipeline/judge_weights.json;
    - make "weighted" the default in score.py;
    - rescore every panel.
  If not: report, and keep two-thirds.

ALSO REPORTED (not criteria)
  - The same rule scored in-sample (weights from both datasets, on both), which is optimistic.
  - The plain three- and four-model panels, out of sample.
  - Every verdict that changes against the current rule in each rescored panel.
  - The expected number of score changes in a rerun of round 2b's panel 1 (judge-level resampling).

Writes reports/calibration_numbers_weighted.json and reports/judge_weights_numbers.json.
"""
import argparse, csv, json, os, random, shutil, statistics, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import score  # noqa: E402

CAL = os.path.join(ROOT, "pipeline", "calibration")
GROUP = {"haiku": "anthropic/claude-haiku-5-5", "sonnet": "anthropic/claude-sonnet-5-5", "opus": "anthropic/claude-opus-5-5",
         "fable": "anthropic/claude-fable-5-2"}
CAL_PANELS = {  # label: (analyse.py args, source of the per-model r, model labels)
    "Claude: haiku, sonnet, opus, with personas": (
        ["--group", "haiku-persona=%s/answers_persona/haiku" % CAL, "--group", "sonnet-persona=%s/answers_persona/sonnet" % CAL,
         "--group", "opus-persona=%s/answers_persona/opus" % CAL, "--panel", "haiku-persona,sonnet-persona,opus-persona"],
        ("calibration_numbers_persona_noise.json", "Claude: haiku, sonnet, opus, with personas"), ["haiku-persona", "sonnet-persona", "opus-persona"]),
    "Claude: haiku, sonnet, opus": (["--panel", "haiku,sonnet,opus"], ("calibration_numbers_persona_noise.json", "Claude: haiku, sonnet, opus"),
                                    ["haiku", "sonnet", "opus"]),
    "Claude: haiku, sonnet, opus, fable": ([], ("calibration_numbers.json", None), ["haiku", "sonnet", "opus", "fable"]),
}
PRIMARY = "Claude: haiku, sonnet, opus, with personas"
EARLIER = {  # the two earlier rules' calibration numbers, for comparison
    "three_quarters": ("calibration_numbers_persona_noise.json", "calibration_numbers.json"),
    "two_thirds": ("calibration_numbers_two_thirds.json", "calibration_numbers.json"),
}
PANELS = [  # rescored with the persona weights (three persona models) or the plain weights (the pilot's four models)
    ("pilot, Claude panel (4 judge models)", ["--run", "main"], "out", "plain4"),
    ("round 2", ["--vignettes", "round2/vignettes.json", "--run", "round2", "--audit-run", "main,round2"], "out/round2", "persona"),
    ("round 2b, panel 1", ["--vignettes", "round2/vignettes_b.json", "--run", "round2b", "--audit-run", "main,round2,round2b"], "out/round2b", "persona"),
    ("round 2b, panel 2", ["--vignettes", "round2/vignettes_b.json", "--run", "round2b-p2", "--audit-run", "main,round2,round2b"], "out/round2b_p2", "persona"),
    ("round 2b, both panels pooled", ["--vignettes", "round2/vignettes_b.json", "--run", "round2b,round2b-p2", "--audit-run", "main,round2,round2b"], "out/round2b_pooled", "persona"),
]


def load(name, key):
    d = json.load(open(os.path.join(ROOT, "reports", name)))
    return d[key] if key else d


def per_model_r(label):
    name, key = CAL_PANELS[label][1]
    d = load(name, key)
    return {m: (d["otr"]["agreement_per_model"][m]["pearson_r"], d["moca"]["agreement_per_model"][m]["pearson_r"]) for m in CAL_PANELS[label][2]}


def weights(rs, which):
    f = {"both": lambda o, m: (o + m) / 2, "otr": lambda o, m: o, "moca": lambda o, m: m}[which]
    return {k: round(max(0.0, f(o, m)), 4) for k, (o, m) in rs.items()}


def table(src, part):
    t = src[part]["verdict_table"]
    return {"confirmed": src[part]["rates"]["panel_confirmed"], "hits": t.get("hit", 0), "false_positives": t.get("false positive", 0),
            "sign_errors": t.get("sign error", 0)}


def combine(o, m):
    c = {k: o[k] + m[k] for k in o}
    c["share_backed_by_people"] = round(c["hits"] / c["confirmed"], 3) if c["confirmed"] else None
    c["otr"], c["moca"] = o, m
    return c


def read(path):
    return {r["pair_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def run_score(args, out, rule, wfile=None):
    extra = ["--judge-weights", wfile] if wfile else []
    subprocess.run([sys.executable, os.path.join(ROOT, "score.py"), *args, "--out", out, "--no-report", "--agreement-rule", rule, *extra],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return read(os.path.join(out, "pair_scores.csv"))


def expected_rerun_changes(rule, X, w, n_outer, n_inner, seed):
    score.set_agreement_rule(rule)
    if w:
        score.set_judge_weights(w)
    V = {p["pair_id"]: p for p in json.load(open(os.path.join(ROOT, "round2", "vignettes_b.json")))["pairs"]}
    rows = score.load_judgments(os.path.join(ROOT, "judgments.csv"), "round2b")
    units = {}
    for r in rows:
        units.setdefault((r["judge_group"], r["repeat"]), {}).setdefault(r["pair_id"], {}).setdefault(r["version"], []).append(r["rating"])
    authored = [p for p in V if V[p]["pair_type"] == "authored"]
    rng = random.Random(seed)
    groups = sorted({u[0] for u in units})
    sims = {p: [] for p in authored}
    for _ in range(n_outer):
        cells = {p: {"A": {}, "B": {}} for p in authored}
        for g in groups:
            pool = [u for u in units if u[0] == g]
            for u in rng.choices(pool, k=len(pool)):
                for p in authored:
                    for v, xs in units[u].get(p, {}).items():
                        cells[p][v].setdefault(g, []).extend(xs)
        for p in authored:
            es = score.effect_stats(cells[p], n_inner, rng)
            sims[p].append(score.prediction_score_distance(V[p]["prediction"], score.classify(es), es["effect"], V[p]["pair_type"])["score"])
    return round(sum(sum(abs(s - float(X[p]["prediction_score"])) > 0.25 for s in sims[p]) / n_outer for p in authored), 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--moral-evals", required=True)
    ap.add_argument("--moca", required=True)
    ap.add_argument("--n-outer", type=int, default=300)
    ap.add_argument("--n-inner", type=int, default=400)
    ap.add_argument("--seed", type=int, default=20261126)
    a = ap.parse_args()
    tmp = tempfile.mkdtemp()
    res = {"rule": "weighted", "definition": "pipeline/test_judge_weights.py docstring", "weights": {}, "calibration": {}, "panels": {}}

    # 1. weights, and the calibration runs (all nine in parallel)
    jobs, raw = {}, {}
    for label, (args, _, models) in CAL_PANELS.items():
        rs = per_model_r(label)
        res["weights"][label] = {"r_otr_moca": {k: list(v) for k, v in rs.items()},
                                 **{which: weights(rs, which) for which in ("both", "otr", "moca")}}
        for which in ("both", "otr", "moca"):
            wf = os.path.join(tmp, "w_%d_%s.json" % (len(jobs), which))
            json.dump(res["weights"][label][which], open(wf, "w"))
            out = os.path.join(tmp, "cal_%d.json" % len(jobs))
            p = subprocess.Popen([sys.executable, os.path.join(CAL, "analyse.py"), "--answers", os.path.join(CAL, "answers"),
                                  "--moral-evals", a.moral_evals, "--moca", a.moca, *args, "--boot", "4000", "--splits", "400",
                                  "--agreement-rule", "weighted", "--judge-weights", wf, "--out", out],
                                 cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            jobs[(label, which)] = (p, out)
    for k, (p, out) in jobs.items():
        _, err = p.communicate()
        if p.returncode != 0:
            raise SystemExit("calibration run %s failed: %s" % (k, err[-2000:]))
        raw[k] = json.load(open(out))
    json.dump({"%s | weights from %s" % k: v for k, v in raw.items()}, open(os.path.join(ROOT, "reports", "calibration_numbers_weighted.json"), "w"), indent=1)
    for label in CAL_PANELS:
        row = {}
        for rule, (f3, f4) in EARLIER.items():
            src = load(f3, label) if label != "Claude: haiku, sonnet, opus, fable" else load(f4, None)
            row[rule] = combine(table(src, "otr"), table(src, "moca"))
        row["weighted, out of sample"] = combine(table(raw[(label, "moca")], "otr"), table(raw[(label, "otr")], "moca"))
        row["weighted, in sample"] = combine(table(raw[(label, "both")], "otr"), table(raw[(label, "both")], "moca"))
        res["calibration"][label] = row

    # 2. the benchmark's panels
    wfiles = {}
    for kind, label in (("persona", PRIMARY), ("plain4", "Claude: haiku, sonnet, opus, fable")):
        w = {GROUP[m.split("-")[0]]: v for m, v in res["weights"][label]["both"].items()}
        wfiles[kind] = os.path.join(tmp, "judge_weights_%s.json" % kind)
        json.dump(w, open(wfiles[kind], "w"))
        res["weights"]["score.py, %s" % kind] = w
    rescored = {}
    for label, args, pub, kind in PANELS:
        cur = read(os.path.join(ROOT, pub, "pair_scores.csv"))
        new = run_score(args, os.path.join(tmp, "new"), "weighted", wfiles[kind])
        rescored[label] = new
        authored = [p for p in new if new[p]["pair_type"] == "authored"]
        tiers = sorted({new[p]["author_tier"] for p in authored})
        changed = [{"pair": p, "type": new[p]["pair_type"], "effect": [round(float(cur[p]["effect"]), 2), round(float(new[p]["effect"]), 2)],
                    "verdict": [cur[p]["observed_direction"], new[p]["observed_direction"]],
                    "score": [round(float(cur[p]["prediction_score"]), 2), round(float(new[p]["prediction_score"]), 2)]}
                   for p in new if cur[p]["observed_direction"] != new[p]["observed_direction"]
                   or abs(float(cur[p]["prediction_score"]) - float(new[p]["prediction_score"])) > 1e-9]
        nulls = lambda X: sum(X[p]["observed_direction"] in ("A_higher", "B_higher") for p in X if X[p]["pair_type"] == "control_null")
        res["panels"][label] = {
            "published_folder": pub, "weights": kind, "changed_vs_current_rule": changed,
            "classic_controls_reproduced": [sum(X[p]["gap_demonstrated"] == "True" for p in X if X[p]["pair_type"] == "control_classic") for X in (cur, new)],
            "nulls_confirmed": [nulls(cur), nulls(new)],
            "authors": {t: {"prediction": [round(statistics.mean(float(X[p]["prediction_score"]) for p in authored if X[p]["author_tier"] == t), 3) for X in (cur, new)],
                            "composite": [round(statistics.mean(float(X[p]["composite"]) for p in authored if X[p]["author_tier"] == t), 1) for X in (cur, new)]}
                        for t in tiers}}

    # 3. stability
    p1, p2 = rescored["round 2b, panel 1"], rescored["round 2b, panel 2"]
    cur1, cur2 = read(os.path.join(ROOT, "out/round2b/pair_scores.csv")), read(os.path.join(ROOT, "out/round2b_p2/pair_scores.csv"))
    authored = [p for p in p1 if p1[p]["pair_type"] == "authored"]
    actual = [p for p in authored if abs(float(p1[p]["prediction_score"]) - float(p2[p]["prediction_score"])) > 0.25]
    res["stability"] = {"authored_pairs": len(authored),
                        "score_changes_over_0.25_panel1_vs_panel2": {
                            "three_quarters (published)": 5,
                            "two_thirds (current)": sum(1 for p in authored if abs(float(cur1[p]["prediction_score"]) - float(cur2[p]["prediction_score"])) > 0.25),
                            "weighted": len(actual)},
                        "weighted_pairs_that_change": actual}
    pw = json.load(open(wfiles["persona"]))
    exp = {}
    for rule, w in (("two_thirds", None), ("weighted", pw)):
        X = run_score(PANELS[2][1], os.path.join(tmp, "x_" + rule), rule, wfiles["persona"] if w else None)
        exp[rule] = expected_rerun_changes(rule, X, w, a.n_outer, a.n_inner, a.seed)
    res["stability"]["expected_score_changes_in_a_rerun_of_panel1"] = exp
    shutil.rmtree(tmp)

    # 4. criteria
    pc = res["calibration"][PRIMARY]["weighted, out of sample"]
    c1 = pc["share_backed_by_people"] is not None and pc["share_backed_by_people"] >= 0.50 and pc["hits"] >= 12
    c2 = len(actual) <= 2
    c3 = all(r["nulls_confirmed"][1] <= r["nulls_confirmed"][0] for r in res["panels"].values())
    res["criteria"] = {"C1_validity_out_of_sample": {"pass": c1, "share_backed_by_people": pc["share_backed_by_people"], "hits": pc["hits"],
                                                     "needs": "share >= 0.50 and hits >= 12"},
                       "C2_stability": {"pass": c2, "score_changes": len(actual), "needs": "<= 2 of 27"},
                       "C3_sanity": {"pass": c3, "needs": "no panel confirms more nulls than under the current rule"},
                       "adopt": c1 and c2 and c3}
    out = os.path.join(ROOT, "reports", "judge_weights_numbers.json")
    json.dump(res, open(out, "w"), indent=1)

    for label, w in res["weights"].items():
        print("weights", label, json.dumps(w))
    for label, row in res["calibration"].items():
        print("calibration:", label)
        for r, x in row.items():
            print("   %-26s confirmed %2d  backed by people %2d  not %2d  sign errors %d  share %s   (OTR %s, MoCa %s)" % (
                r, x["confirmed"], x["hits"], x["false_positives"], x["sign_errors"], x["share_backed_by_people"], x["otr"], x["moca"]))
    for label, r in res["panels"].items():
        print("%-40s changed %2d  classic %s  nulls %s" % (label, len(r["changed_vs_current_rule"]), r["classic_controls_reproduced"], r["nulls_confirmed"]))
        for c in r["changed_vs_current_rule"]:
            print("     %-34s %-15s gap %s  %s -> %s  score %s -> %s" % (c["pair"], c["type"], c["effect"], c["verdict"][0], c["verdict"][1], c["score"][0], c["score"][1]))
        print("     authors:", json.dumps(r["authors"]))
    print("stability:", json.dumps(res["stability"]))
    print("criteria:", json.dumps(res["criteria"]))
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
