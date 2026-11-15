#!/usr/bin/env python3
"""Compare the human panel with the model panel, pair by pair.

    python3 compare_panels.py                       # runs "human-1" against "main"
    python3 compare_panels.py --human-run human-1 --model-run main --min-per-version 8

Uses the same effect, interval and gap rules as score.py. Writes
out/panel_comparison.csv and prints the summary the methods note asks for.

Exclusions, fixed before any human data existed (see docs/human-survey.md):
a participant is dropped if they answered at least five scenarios and got
fewer than 80% of the factual questions right, or if their median time per
scenario was under eight seconds. Pass --keep-all to see the result without
exclusions.
"""
import argparse, csv, json, math, os, random, statistics, zlib
from collections import defaultdict
import score as S

ROOT = os.path.dirname(os.path.abspath(__file__))


def pearson(xs, ys):
    if len(xs) < 3 or statistics.pstdev(xs) == 0 or statistics.pstdev(ys) == 0:
        return None
    mx, my = S.mean(xs), S.mean(ys)
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (len(xs) * statistics.pstdev(xs) * statistics.pstdev(ys))


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--human-run", default="human-1")
    ap.add_argument("--model-run", default="main")
    ap.add_argument("--min-per-version", type=int, default=8, help="fewest human ratings per version for a pair to count")
    ap.add_argument("--boot", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--keep-all", action="store_true", help="skip the participant exclusions")
    args = ap.parse_args()

    doc = json.load(open(os.path.join(args.root, "vignettes.json"), encoding="utf-8"))
    key = {p["pair_id"]: p["comprehension_question"]["correct"] for p in doc["pairs"]}
    H = S.load_judgments(os.path.join(args.root, "judgments.csv"), args.human_run)
    M = S.load_judgments(os.path.join(args.root, "judgments.csv"), args.model_run)
    if not H:
        raise SystemExit("no judgments for run %r yet: ingest completion codes with pipeline/ingest_survey.py first" % args.human_run)

    # ---- participant exclusions
    by_person = defaultdict(list)
    for r in H:
        by_person[r["judge_id"]].append(r)
    med = {}
    ppath = os.path.join(args.root, "participants.csv")
    if os.path.exists(ppath):
        for r in csv.DictReader(open(ppath, encoding="utf-8")):
            if r["run_id"] == args.human_run and r["median_seconds"] != "":
                med["human/" + r["participant"]] = float(r["median_seconds"])
    dropped = {}
    for jid, rows in by_person.items():
        acc = S.mean([1.0 if r["comprehension_answer"].strip().lower() == key[r["pair_id"]][r["version"]] else 0.0 for r in rows])
        if len(rows) >= 5 and acc < 0.8:
            dropped[jid] = "factual questions %.0f%% right" % (100 * acc)
        elif jid in med and med[jid] < 8:
            dropped[jid] = "median %.0f s per scenario" % med[jid]
    if args.keep_all:
        dropped = {}
    H = [r for r in H if r["judge_id"] not in dropped]

    def cells(rows):
        c = defaultdict(lambda: {"A": defaultdict(list), "B": defaultdict(list)})
        for r in rows:
            c[r["pair_id"]][r["version"]][r["judge_group"]].append(r["rating"])
        return c
    ch, cm = cells(H), cells(M)

    out = []
    for p in doc["pairs"]:
        pid = p["pair_id"]
        n_a = sum(len(v) for v in ch[pid]["A"].values())
        n_b = sum(len(v) for v in ch[pid]["B"].values())
        rec = {"pair_id": pid, "pair_type": p["pair_type"], "factor_id": p["factor_id"],
               "author": p["author"].get("tier", "") or p["author"]["author_id"],
               "predicted": "%s/%s" % (p["prediction"]["direction"], p["prediction"]["size"]),
               "human_n_a": n_a, "human_n_b": n_b}
        em = S.effect_stats(cm[pid], args.boot, random.Random(zlib.crc32(("m%d|%s" % (args.seed, pid)).encode())))
        if em:
            om = S.classify(em)
            rec.update({"model_effect": em["effect"], "model_direction": om["direction"], "model_size": om["size"]})
        if min(n_a, n_b) >= args.min_per_version:
            eh = S.effect_stats(ch[pid], args.boot, random.Random(zlib.crc32(("h%d|%s" % (args.seed, pid)).encode())))
            oh = S.classify(eh)
            ps = S.prediction_score(p["prediction"], oh, eh["effect"])
            rec.update({"human_mean_a": eh["mean_a"], "human_mean_b": eh["mean_b"], "human_effect": eh["effect"],
                        "human_ci_low": eh["ci_low"], "human_ci_high": eh["ci_high"], "human_direction": oh["direction"],
                        "human_size": oh["size"], "human_std_effect": eh["std_effect"],
                        "prediction_direction_hit_on_people": ps["direction_hit"], "prediction_size_hit_on_people": ps["size_hit"]})
            if em:
                rec["panels_agree_on_direction"] = oh["direction"] == om["direction"]
        out.append(rec)

    os.makedirs(os.path.join(args.root, "out"), exist_ok=True)
    cols = ["pair_id", "pair_type", "factor_id", "author", "predicted", "human_n_a", "human_n_b", "human_mean_a",
            "human_mean_b", "human_effect", "human_ci_low", "human_ci_high", "human_direction", "human_size",
            "human_std_effect", "model_effect", "model_direction", "model_size", "panels_agree_on_direction",
            "prediction_direction_hit_on_people", "prediction_size_hit_on_people"]
    with open(os.path.join(args.root, "out", "panel_comparison.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in out:
            w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in cols})

    usable = [r for r in out if "human_effect" in r and "model_effect" in r]
    print("human run %r: %d participants kept, %d dropped%s" % (
        args.human_run, len({r["judge_id"] for r in H}), len(dropped),
        (" (" + "; ".join("%s: %s" % (k.split("/")[-1], v) for k, v in dropped.items()) + ")") if dropped else ""))
    print("pairs with at least %d human ratings per version: %d of %d" % (args.min_per_version, len(usable), len(out)))
    if not usable:
        print("not enough human data yet for any pair")
        return
    hx, mx = [r["human_effect"] for r in usable], [r["model_effect"] for r in usable]
    r_p, r_s = pearson(hx, mx), pearson(ranks(hx), ranks(mx))
    slope = sum(a * b for a, b in zip(hx, mx)) / sum(a * a for a in hx) if any(hx) else None
    fmt = lambda x: "n/a" if x is None else "%.2f" % x
    print("gap in people vs gap in models across pairs: correlation %s (rank %s); model gap per point of human gap %s" % (fmt(r_p), fmt(r_s), fmt(slope)))
    print("panels agree on direction (including 'no gap'): %d of %d" % (sum(1 for r in usable if r["panels_agree_on_direction"]), len(usable)))
    for kind, label in (("control_classic", "classic controls showing the expected direction in people"),
                        ("control_null", "null controls showing a gap in people")):
        rs = [r for r in usable if r["pair_type"] == kind]
        if kind == "control_classic":
            k = sum(1 for r in rs if r["prediction_direction_hit_on_people"])
        else:
            k = sum(1 for r in rs if r["human_direction"] in ("A_higher", "B_higher"))
        print("%s: %d of %d" % (label, k, len(rs)))
    au = [r for r in usable if r["pair_type"] == "authored"]
    print("authored pairs whose predicted direction held in people: %d of %d (direction and size: %d)" % (
        sum(1 for r in au if r["prediction_direction_hit_on_people"]), len(au),
        sum(1 for r in au if r["prediction_direction_hit_on_people"] and r["prediction_size_hit_on_people"])))
    for a in sorted({r["author"] for r in au}):
        rs = [r for r in au if r["author"] == a]
        print("   %-8s %d of %d" % (a, sum(1 for r in rs if r["prediction_direction_hit_on_people"]), len(rs)))
    print("wrote", os.path.join(args.root, "out", "panel_comparison.csv"))


if __name__ == "__main__":
    main()
