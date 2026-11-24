#!/usr/bin/env python3
"""What the 24 November agreement-rule change did: the pilot's rule (three_quarters: 3 of 3 judge groups, 3 of 4)
against the new one (two_thirds: 2 of 3, 3 of 4).

    python3 pipeline/compare_agreement_rules.py [--before 3c8a99c]

"Before" is read from git at --before (the last commit scored under the old rule); "after" is the working tree, scored
under the new rule. Writes reports/agreement_rule_numbers.json. The old scores can also be rebuilt from the data with
`python3 score.py ... --agreement-rule three_quarters`.

Also compares the calibration on public human data for the two three-model Claude panels: the old rule's numbers are in
reports/calibration_numbers_persona_noise.json, the new rule's in reports/calibration_numbers_two_thirds.json (built
by pipeline/calibration/analyse.py --agreement-rule two_thirds, with the same arguments as the persona-noise runs).
"""
import argparse, csv, io, json, os, statistics, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = [("pilot, Claude panel (4 judge models)", "out"),
        ("pilot, same 3 judge models", "out/main_same_models"),
        ("pilot, persona panel (3 judge models)", "out/persona"),
        ("pilot, Gemini (2 models)", "out/gemini"),
        ("pilot, Claude and Gemini as two groups", "out/vendor_groups"),
        ("pilot, 4 Claude + 2 Gemini models (6 groups)", "out/claude_plus_gemini"),
        ("round 2 (3 judge models)", "out/round2"),
        ("round 2b, panel 1", "out/round2b"),
        ("round 2b, panel 2", "out/round2b_p2"),
        ("round 2b, both panels pooled", "out/round2b_pooled")]


def read(text):
    return {r["pair_id"]: r for r in csv.DictReader(io.StringIO(text))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", default="3c8a99c")
    args = ap.parse_args()
    res = {"before_commit": args.before, "runs": {}}
    for label, d in RUNS:
        old = read(subprocess.run(["git", "show", "%s:%s/pair_scores.csv" % (args.before, d)], cwd=ROOT, capture_output=True,
                                  text=True, check=True).stdout)
        new = read(open(os.path.join(ROOT, d, "pair_scores.csv"), encoding="utf-8").read())
        assert set(old) == set(new), d
        changed = []
        for p in new:
            o, n = old[p], new[p]
            if o["observed_direction"] != n["observed_direction"] or abs(float(o["prediction_score"]) - float(n["prediction_score"])) > 1e-9:
                changed.append({"pair": p, "type": n["pair_type"], "effect": round(float(n["effect"]), 2),
                                "groups": "%s/%s" % (n["groups_same_sign"], n["groups_total"]),
                                "verdict": [o["observed_direction"], n["observed_direction"]],
                                "score": [round(float(o["prediction_score"]), 2), round(float(n["prediction_score"]), 2)]})
        authored = [p for p in new if new[p]["pair_type"] == "authored"]
        tiers = sorted({new[p]["author_tier"] for p in authored})
        def mean(X, key, t):
            v = [float(X[p][key]) for p in authored if X[p]["author_tier"] == t and X[p][key] not in ("", None)]
            return round(statistics.mean(v), 3) if v else None
        res["runs"][label] = {
            "dir": d, "n_pairs": len(new), "changed": changed,
            "classic_controls_reproduced": [sum(X[p]["gap_demonstrated"] == "True" for p in X if X[p]["pair_type"] == "control_classic")
                                            for X in (old, new)],
            "nulls_confirmed": [sum(X[p]["observed_direction"] in ("A_higher", "B_higher") for p in X if X[p]["pair_type"] == "control_null")
                                for X in (old, new)],
            "authored_demonstrated": [sum(X[p]["gap_demonstrated"] == "True" for p in authored) for X in (old, new)],
            "authors": {t: {"prediction": [mean(old, "prediction_score", t), mean(new, "prediction_score", t)],
                            "composite": [mean(old, "composite", t), mean(new, "composite", t)]} for t in tiers}}
    # calibration on public human data, three-model Claude panels
    old_c = json.load(open(os.path.join(ROOT, "reports", "calibration_numbers_persona_noise.json")))
    new_c = json.load(open(os.path.join(ROOT, "reports", "calibration_numbers_two_thirds.json")))
    cal = {}
    for k in new_c:
        row = {}
        for rule, src in (("three_quarters", old_c[k]), ("two_thirds", new_c[k])):
            ot, mt = src["otr"]["verdict_table"], src["moca"]["verdict_table"]
            hits = ot.get("hit", 0) + mt.get("hit", 0)
            fps = ot.get("false positive", 0) + mt.get("false positive", 0)
            conf = src["otr"]["rates"]["panel_confirmed"] + src["moca"]["rates"]["panel_confirmed"]
            row[rule] = {"otr": {"confirmed": src["otr"]["rates"]["panel_confirmed"], "hits": ot.get("hit", 0),
                                 "false_positives": ot.get("false positive", 0), "sign_errors": ot.get("sign error", 0),
                                 "human_nulls": src["otr"]["rates"]["human_nulls"]},
                         "moca": {"confirmed": src["moca"]["rates"]["panel_confirmed"], "hits": mt.get("hit", 0),
                                  "false_positives": mt.get("false positive", 0), "human_nulls": src["moca"]["rates"]["human_nulls"]},
                         "both": {"confirmed": conf, "hits": hits, "false_positives": fps,
                                  "share_of_confirmed_backed_by_people": round(hits / conf, 3) if conf else None}}
        cal[k] = row
    res["calibration"] = cal
    out = os.path.join(ROOT, "reports", "agreement_rule_numbers.json")
    json.dump(res, open(out, "w"), indent=1)
    for label, r in res["runs"].items():
        print("%-46s changed %2d  classic %s  nulls %s  demonstrated %s" % (label, len(r["changed"]), r["classic_controls_reproduced"],
                                                                            r["nulls_confirmed"], r["authored_demonstrated"]))
        for c in r["changed"]:
            print("     %-34s %-15s %+.2f %s %s -> %s  score %s -> %s" % (c["pair"], c["type"], c["effect"], c["groups"], c["verdict"][0],
                                                                       c["verdict"][1], c["score"][0], c["score"][1]))
        print("     authors:", json.dumps(r["authors"]))
    for k, row in cal.items():
        print("calibration", k, json.dumps(row))
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
