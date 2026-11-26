#!/usr/bin/env python3
"""Test of the "cheaper fix" for the ceiling veto, run before deciding whether to adopt it.

    python3 pipeline/test_ceiling_abstain.py --moral-evals DIR --moca DIR

Requested by the owner on 26 November 2026 ("go ahead with the cheaper fix"). This file, with the rule's code in
score.py and pipeline/calibration/analyse.py, was committed BEFORE the test was run. The criteria below are fixed here.

THE RULE ("ceiling_abstain")
  The pilot's rule: three quarters of the judge groups must agree on a gap's sign (3 of 3, 3 of 4). But a judge group
  whose mean for BOTH versions lies in the top twelfth of the scale (>= 6.5 on 1-7, >= 4.67 on OffTheRails' 1-5, a
  yes-share >= 0.917 on MoCa) or BOTH in the bottom twelfth abstains. It stays in the averaged gap and its interval,
  but doesn't vote on the sign. A gap then needs three quarters of the voting groups, and at least two of them.
  Why: under the pilot's rule a judge model at the scale's top could veto a gap the others showed clearly, and that
  caused most of the verdict flips between panels. The two-thirds rule (24 November) fixed the flips, but on public
  human data it doubled the gaps the persona panel confirms that people don't show (10 -> 20).

CRITERIA (all three must pass for adoption; otherwise the two-thirds rule stays)
  C1 validity. On the public human data (OffTheRails and MoCa together), the three-model persona Claude panel, the
     panel rounds 2 and 2b used: at least 50% of the gaps it confirms are backed by people (pilot rule 55%, two-thirds
     39%), and it confirms at least 12 of the gaps people show (pilot rule 12, two-thirds 13).
  C2 stability. Round 2b, panel 1 against panel 2: at most 2 of the 27 authored pairs change prediction score by more
     than 0.25 (pilot rule 5, two-thirds 1).
  C3 sanity. No null control is confirmed in any rescored panel.
  If all pass: make "ceiling_abstain" the default in score.py and rescore every panel. If not: report and keep
  two-thirds.

ALSO REPORTED (not criteria)
  The plain three- and four-model Claude panels on the human data; the expected number of score changes in a rerun of
  round 2b's panel 1 (judge-level resampling, all three rules computed here, same seed); every verdict that changes
  against the current rule in every rescored panel; classic controls reproduced; author means.

Writes reports/calibration_numbers_ceiling_abstain.json (the calibration runs) and reports/ceiling_abstain_numbers.json.
"""
import argparse, csv, json, os, random, shutil, statistics, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import score  # noqa: E402

CAL = os.path.join(ROOT, "pipeline", "calibration")
CAL_PANELS = [  # label, extra args, where the earlier rules' numbers are
    ("Claude: haiku, sonnet, opus, with personas",
     ["--group", "haiku-persona=%s/answers_persona/haiku" % CAL, "--group", "sonnet-persona=%s/answers_persona/sonnet" % CAL,
      "--group", "opus-persona=%s/answers_persona/opus" % CAL, "--panel", "haiku-persona,sonnet-persona,opus-persona"]),
    ("Claude: haiku, sonnet, opus", ["--panel", "haiku,sonnet,opus"]),
    ("Claude: haiku, sonnet, opus, fable", []),
]
PANELS = [  # label, score.py arguments, published folder (scored under the current rule)
    ("pilot, Claude panel (4 judge models)", ["--run", "main"], "out"),
    ("pilot, persona panel (4 judge models)", ["--run", "persona", "--audit-run", "main"], "out/persona"),
    ("round 2", ["--vignettes", "round2/vignettes.json", "--run", "round2", "--audit-run", "main,round2"], "out/round2"),
    ("round 2b, panel 1", ["--vignettes", "round2/vignettes_b.json", "--run", "round2b", "--audit-run", "main,round2,round2b"], "out/round2b"),
    ("round 2b, panel 2", ["--vignettes", "round2/vignettes_b.json", "--run", "round2b-p2", "--audit-run", "main,round2,round2b"], "out/round2b_p2"),
    ("round 2b, both panels pooled", ["--vignettes", "round2/vignettes_b.json", "--run", "round2b,round2b-p2", "--audit-run", "main,round2,round2b"], "out/round2b_pooled"),
    ("round 2c (4 judge models)", ["--vignettes", "round2/vignettes_c.json", "--run", "round2c", "--audit-run", "main,round2,round2b,round2c"], "out/round2c"),
]


def read(path):
    return {r["pair_id"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}


def cal_summary(src):
    ot, mt = src["otr"]["verdict_table"], src["moca"]["verdict_table"]
    conf = src["otr"]["rates"]["panel_confirmed"] + src["moca"]["rates"]["panel_confirmed"]
    hits = ot.get("hit", 0) + mt.get("hit", 0)
    return {"confirmed": conf, "hits": hits, "false_positives": ot.get("false positive", 0) + mt.get("false positive", 0),
            "sign_errors": ot.get("sign error", 0) + mt.get("sign error", 0),
            "otr": {"confirmed": src["otr"]["rates"]["panel_confirmed"], "hits": ot.get("hit", 0), "false_positives": ot.get("false positive", 0)},
            "moca": {"confirmed": src["moca"]["rates"]["panel_confirmed"], "hits": mt.get("hit", 0), "false_positives": mt.get("false positive", 0)},
            "share_backed_by_people": round(hits / conf, 3) if conf else None}


def run_score(args, out, rule):
    subprocess.run([sys.executable, os.path.join(ROOT, "score.py"), *args, "--out", out, "--no-report", "--agreement-rule", rule],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return read(os.path.join(out, "pair_scores.csv"))


def expected_rerun_changes(rule, X, n_outer, n_inner, seed):
    """Judge-level resampling of round 2b panel 1, as in pipeline/round2/analyse_panels.py, under one rule."""
    score.set_agreement_rule(rule)
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
    res = {"rule": "ceiling_abstain", "definition": "pipeline/test_ceiling_abstain.py docstring", "calibration": {}, "panels": {}}

    # 1. the human data
    old_c = json.load(open(os.path.join(ROOT, "reports", "calibration_numbers_persona_noise.json")))
    tt_c = json.load(open(os.path.join(ROOT, "reports", "calibration_numbers_two_thirds.json")))
    four = json.load(open(os.path.join(ROOT, "reports", "calibration_numbers.json")))
    new_c = {}
    tmp = tempfile.mkdtemp()
    for label, extra in CAL_PANELS:
        out = os.path.join(tmp, "cal.json")
        subprocess.run([sys.executable, os.path.join(CAL, "analyse.py"), "--answers", os.path.join(CAL, "answers"), "--moral-evals",
                        a.moral_evals, "--moca", a.moca, *extra, "--boot", "4000", "--splits", "400", "--agreement-rule", "ceiling_abstain",
                        "--out", out], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        new_c[label] = json.load(open(out))
        earlier = {"three_quarters": old_c[label], "two_thirds": tt_c[label]} if label in old_c else {"three_quarters": four, "two_thirds": four}
        row = {r: cal_summary(src) for r, src in earlier.items()}
        row["ceiling_abstain"] = cal_summary(new_c[label])
        row["ceiling_abstain"]["moca_pairs_with_an_abstaining_group"] = sum(1 for r in new_c[label]["moca"]["pairs"] if r.get("abstaining"))
        res["calibration"][label] = row
    json.dump(new_c, open(os.path.join(ROOT, "reports", "calibration_numbers_ceiling_abstain.json"), "w"), indent=1)

    # 2. every scored panel, rescored under the rule (into a temporary folder; the published folders are untouched)
    rescored = {}
    for label, args, pub in PANELS:
        cur = read(os.path.join(ROOT, pub, "pair_scores.csv"))
        check = run_score(args, os.path.join(tmp, "check"), "two_thirds")
        reproduces = all(check[p]["observed_direction"] == cur[p]["observed_direction"] and check[p]["prediction_score"] == cur[p]["prediction_score"]
                         for p in cur) and set(check) == set(cur)
        new = run_score(args, os.path.join(tmp, "new"), "ceiling_abstain")
        newjson = json.load(open(os.path.join(tmp, "new", "results.json")))
        abst = {p["pair_id"]: p["effect"].get("groups_abstaining", []) for p in newjson["pairs"]}
        rescored[label] = new
        authored = [p for p in new if new[p]["pair_type"] == "authored"]
        tiers = sorted({new[p]["author_tier"] for p in authored})
        changed = []
        for p in new:
            o, n = cur[p], new[p]
            if o["observed_direction"] != n["observed_direction"] or abs(float(o["prediction_score"]) - float(n["prediction_score"])) > 1e-9:
                changed.append({"pair": p, "type": n["pair_type"], "effect": round(float(n["effect"]), 2),
                                "voting_groups_agreeing": "%s/%s" % (n["groups_same_sign"], n["groups_total"]), "abstaining": abst[p],
                                "verdict": [o["observed_direction"], n["observed_direction"]],
                                "score": [round(float(o["prediction_score"]), 2), round(float(n["prediction_score"]), 2)]})
        res["panels"][label] = {
            "published_folder": pub, "current_rule_reproduces_published": reproduces, "changed_vs_current_rule": changed,
            "pairs_with_an_abstaining_group": sum(1 for p in abst if abst[p]),
            "classic_controls_reproduced": {"current": sum(cur[p]["gap_demonstrated"] == "True" for p in cur if cur[p]["pair_type"] == "control_classic"),
                                            "ceiling_abstain": sum(new[p]["gap_demonstrated"] == "True" for p in new if new[p]["pair_type"] == "control_classic"),
                                            "of": sum(1 for p in new if new[p]["pair_type"] == "control_classic")},
            "nulls_confirmed": {"current": sum(cur[p]["observed_direction"] in ("A_higher", "B_higher") for p in cur if cur[p]["pair_type"] == "control_null"),
                                "ceiling_abstain": sum(new[p]["observed_direction"] in ("A_higher", "B_higher") for p in new if new[p]["pair_type"] == "control_null")},
            "authors": {t: {"prediction": [round(statistics.mean(float(X[p]["prediction_score"]) for p in authored if X[p]["author_tier"] == t), 3) for X in (cur, new)],
                            "composite": [round(statistics.mean(float(X[p]["composite"]) for p in authored if X[p]["author_tier"] == t), 1) for X in (cur, new)]}
                        for t in tiers}}
    shutil.rmtree(tmp)

    # 3. stability: round 2b panel 1 against panel 2, actual and expected
    p1, p2 = rescored["round 2b, panel 1"], rescored["round 2b, panel 2"]
    authored = [p for p in p1 if p1[p]["pair_type"] == "authored"]
    actual = [p for p in authored if abs(float(p1[p]["prediction_score"]) - float(p2[p]["prediction_score"])) > 0.25]
    cur1, cur2 = read(os.path.join(ROOT, "out/round2b/pair_scores.csv")), read(os.path.join(ROOT, "out/round2b_p2/pair_scores.csv"))
    res["stability"] = {
        "authored_pairs": len(authored),
        "score_changes_over_0.25_panel1_vs_panel2": {
            "three_quarters (published)": 5,
            "two_thirds (current)": sum(1 for p in authored if abs(float(cur1[p]["prediction_score"]) - float(cur2[p]["prediction_score"])) > 0.25),
            "ceiling_abstain": len(actual)},
        "ceiling_abstain_pairs_that_change": actual}
    exp = {}
    tmp2 = tempfile.mkdtemp()
    for rule in ("three_quarters", "two_thirds", "ceiling_abstain"):
        X = run_score(PANELS[3][1], os.path.join(tmp2, rule), rule)
        exp[rule] = expected_rerun_changes(rule, X, a.n_outer, a.n_inner, a.seed)
    shutil.rmtree(tmp2)
    res["stability"]["expected_score_changes_in_a_rerun_of_panel1"] = exp

    # 4. the criteria
    pc = res["calibration"]["Claude: haiku, sonnet, opus, with personas"]["ceiling_abstain"]
    c1 = pc["share_backed_by_people"] is not None and pc["share_backed_by_people"] >= 0.50 and pc["hits"] >= 12
    c2 = len(actual) <= 2
    c3 = all(r["nulls_confirmed"]["ceiling_abstain"] == 0 for r in res["panels"].values())
    res["criteria"] = {"C1_validity": {"pass": c1, "share_backed_by_people": pc["share_backed_by_people"], "hits": pc["hits"],
                                       "needs": "share >= 0.50 and hits >= 12"},
                       "C2_stability": {"pass": c2, "score_changes": len(actual), "needs": "<= 2 of 27"},
                       "C3_sanity": {"pass": c3, "needs": "no null control confirmed in any rescored panel"},
                       "adopt": c1 and c2 and c3}
    out = os.path.join(ROOT, "reports", "ceiling_abstain_numbers.json")
    json.dump(res, open(out, "w"), indent=1)

    for label, row in res["calibration"].items():
        print("calibration:", label)
        for r, x in row.items():
            print("   %-16s confirmed %2d  backed by people %2d  not %2d  sign errors %d  share %s   (OTR %s, MoCa %s)" % (
                r, x["confirmed"], x["hits"], x["false_positives"], x["sign_errors"], x["share_backed_by_people"], x["otr"], x["moca"]))
    for label, r in res["panels"].items():
        print("%-40s reproduces %-5s changed %2d  abstaining on %2d pairs  classic %s  nulls %s" % (
            label, r["current_rule_reproduces_published"], len(r["changed_vs_current_rule"]), r["pairs_with_an_abstaining_group"],
            r["classic_controls_reproduced"], r["nulls_confirmed"]))
        for c in r["changed_vs_current_rule"]:
            print("     %-34s %-15s %+.2f %s abstain %s  %s -> %s  score %s -> %s" % (
                c["pair"], c["type"], c["effect"], c["voting_groups_agreeing"], c["abstaining"], c["verdict"][0], c["verdict"][1], c["score"][0], c["score"][1]))
        print("     authors:", json.dumps(r["authors"]))
    print("stability:", json.dumps(res["stability"]))
    print("criteria:", json.dumps(res["criteria"]))
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
