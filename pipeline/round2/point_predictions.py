#!/usr/bin/env python3
"""A sharper prediction target, tested on data already collected: authors predict each gap as a number.

    python3 pipeline/round2/point_predictions.py build   --out DIR            # one task file per model
    python3 pipeline/round2/point_predictions.py check   --transcripts DIR    # provenance of the prediction agents
    python3 pipeline/round2/point_predictions.py analyse [--answers DIR]      # scores; writes reports/point_predictions_numbers.json

Design (fixed in this file and committed before any prediction was collected, 24 November 2026):

  Items. The 37 round-2b items: the 27 authored pairs on the three new factors (9 each by Haiku, Sonnet and Opus) and
  the 10 controls. Pairs carry neutral codes; authors are not named.
  Predictors. Haiku, Sonnet and Opus, each in a fresh context, each predicting all 37 items without being told which
  pairs are their own. They see the texts and the judgment question, a description of the readers and of the measure,
  and nothing about any result or about anyone's earlier prediction.
  Target. The gap the two pooled round-2b panels measured: the mean over the three judge models of (mean rating of
  version A minus mean rating of version B), 1-7 scale, 10 ratings per model and version (out/round2b_pooled).

  Primary outcome. Each author's mean absolute error on its own 9 pairs (the benchmark's construct: an author predicting
  the pairs it wrote). Secondary: the point score max(0, 1 - |error| / 1.5), on the same 1.5-point scale as the current
  distance rule; mean absolute error and correlation on all 37 items (prediction skill on identical items).
  Baselines. (a) The author's own earlier categorical prediction turned into a number (none 0, small 1.0, large 2.0,
  signed by direction), to see whether a number adds anything over the size classes. (b) The noise floor: the error a
  perfect predictor would still show because the measured gap is itself noisy (se * sqrt(2/pi) per pair).
  Uncertainty. (1) Judge-level resampling: whole repeats (one model's x and y judge) resampled within each judge model
  across both panels, every gap recomputed, every error recomputed (2,000 resamples). (2) A permutation test on own-pair
  errors, shuffling authors among the 9 pairs of each factor (20,000). (3) On all 37 items, a paired sign-flip test of
  the per-item error differences between two predictors (20,000).
  Pass mark, decided in advance: the sharper target "separates Sonnet and Opus" only if their own-pair mean absolute
  errors differ in the same direction in at least 90% of judge-level resamples AND the permutation p is below 0.05.
"""
import argparse, csv, glob, itertools, json, math, os, random, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import score  # noqa: E402

VIGN = os.path.join(ROOT, "round2", "vignettes_b.json")
MANIFEST = os.path.join(HERE, "point_manifest.json")
ANS = os.path.join(HERE, "raw", "point_predictions")
PROV = os.path.join(HERE, "raw", "provenance_points.json")
OUT = os.path.join(ROOT, "reports", "point_predictions_numbers.json")
MODELS = ["haiku", "sonnet", "opus"]
NEW = ["inevitable_harm", "knowledge_causation", "luck_wrongness"]
SCALE = 1.5
RUNS = ("round2b", "round2b-p2")

INTRO = """You are taking part in a benchmark called "Thought-experiment authoring". Authors write pairs of short scenarios that differ in one factor, and a panel of readers judges them. Your task here is to predict, for each of {n} pairs below, how big a difference the readers' judgments showed.

HOW THE READERS JUDGED
- The readers were AI language models from three model tiers. Each reader was asked to answer as a different described adult, with an age, a background and habits of their own (some use the ends of rating scales, some the middle), giving that person's honest judgment.
- Every reader saw only ONE version of a given pair, mixed in random order with 36 other short scenarios from different authors, and answered the judgment question on a scale from 1 to 7.
- For each pair, each version was rated 10 times by each of the three reader models (60 ratings per pair in all).

WHAT TO PREDICT
For each pair, predict the measured gap: the mean rating of version A minus the mean rating of version B, on the 1-7 scale, averaged over the three reader models. A positive number means version A was rated higher; a negative number means version B was rated higher; 0 means no difference. Give a number with one decimal, for example 1.3, -0.6 or 0.0. Possible values run from -6.0 to 6.0; in practice gaps in this study ran from about -2 to about +3.

Predict what the readers actually did, not what they ought to have done. Work from your own knowledge; do not use any tool other than reading this file and writing your answer file.

THE PAIRS
"""
CLOSING = """
YOUR ANSWER
Write your predictions with the Write tool to the output file named in your instructions, as one JSON object of exactly this form, with one entry per pair in the order given:
{"predictions": [{"pair": "P01", "gap": 1.2, "reason": "one short sentence"}, ...]}
"""
INSTRUCTION = ("Read the file {task} with the Read tool and follow its instructions. Read only that one file: do not open any "
               "other file, list folders, run commands, search, or look anything up, and do not use any other tool. When your "
               "predictions are ready, write them with the Write tool to {answer} in exactly the JSON form the file specifies. "
               "Then end your turn with the plain-text reply: done (this needs no tool).")


def load_pairs():
    return {p["pair_id"]: p for p in json.load(open(VIGN, encoding="utf-8"))["pairs"]}


def build(args):
    pairs = load_pairs()
    ids = sorted(pairs)
    rng = random.Random(20261124)
    man = {"seed": 20261124, "instruction": INSTRUCTION, "models": {}}
    os.makedirs(args.out, exist_ok=True)
    for m in MODELS:
        order = ids[:]
        rng.shuffle(order)
        codes = {"P%02d" % (i + 1): pid for i, pid in enumerate(order)}
        parts = []
        for code, pid in codes.items():
            p = pairs[pid]
            q = p["judgment_question"]
            parts.append("PAIR %s\nVersion A:\n%s\n\nVersion B:\n%s\n\nJudgment question (1 = %s; 7 = %s): %s" % (
                code, p["versions"]["A"]["text"], p["versions"]["B"]["text"], q["label_min"], q["label_max"], q["text"]))
        text = INTRO.format(n=len(codes)) + "\n" + "\n\n==========\n\n".join(parts) + "\n" + CLOSING
        open(os.path.join(args.out, m + ".txt"), "w", encoding="utf-8").write(text)
        man["models"][m] = codes
    json.dump(man, open(MANIFEST, "w"), indent=1)
    print("wrote %d task files of %d pairs to %s; manifest %s" % (len(MODELS), len(ids), args.out, os.path.relpath(MANIFEST, ROOT)))


def check(args):
    out = {}
    for f in glob.glob(os.path.join(args.transcripts, "agent-*.jsonl")):
        L = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        first = next((l for l in L if l.get("type") == "user"), None)
        if not first:
            continue
        c = first["message"]["content"]
        t = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
        mm = re.search(r"/r2pt/(\w+)\.txt.*?/r2pta/(\w+)\.json", t, re.S)
        if not mm:
            continue
        model = mm.group(1)
        served, calls = set(), []
        for l in L:
            msg = l.get("message", {})
            if isinstance(msg, dict):
                if msg.get("model"):
                    served.add(msg["model"])
                for x in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
                    if isinstance(x, dict) and x.get("type") == "tool_use" and x["name"] not in ("SubagentHandback", "StructuredOutput"):
                        calls.append([x["name"], os.path.basename((x.get("input") or {}).get("file_path", "") or "")])
        wrote_at = next((i for i, cl in enumerate(calls) if cl[0] == "Write"), None)
        before = calls[:wrote_at] if wrote_at is not None else calls
        after = calls[wrote_at + 1:] if wrote_at is not None else []
        own = model + ".json"
        out["points:" + model] = {"served": sorted(served), "calls": calls,
                                  "usable": wrote_at is not None and calls[wrote_at][1] == own and len(before) >= 1
                                            and all(cl[0] == "Read" and cl[1] == model + ".txt" for cl in before)
                                            and all(cl[1] == own for cl in after if cl[0] in ("Write", "Edit"))}
    json.dump(out, open(PROV, "w"), indent=1)
    for k in sorted(out):
        print("%-16s served %-22s usable %-5s calls %s" % (k, ",".join(out[k]["served"]), out[k]["usable"], [c[0] for c in out[k]["calls"]]))


def gaps_from(units, keys):
    """Mean over judge models of (mean A - mean B) for each pair, from a list of repeat units."""
    acc = {}
    for u in keys:
        g = u[1]
        for pid, vs in units[u].items():
            for v, xs in vs.items():
                acc.setdefault(pid, {}).setdefault(g, {"A": [], "B": []})[v].extend(xs)
    return {pid: statistics.mean(statistics.mean(c["A"]) - statistics.mean(c["B"]) for c in per.values()) for pid, per in acc.items()}


def analyse(args):
    pairs = load_pairs()
    man = json.load(open(MANIFEST))
    prov = json.load(open(PROV)) if os.path.exists(PROV) else {}
    obs = {r["pair_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "out", "round2b_pooled", "pair_scores.csv"), encoding="utf-8"))}
    # the target gaps, recomputed at full precision from the ratings (the CSV rounds them to two decimals)
    rows = score.load_judgments(os.path.join(ROOT, "judgments.csv"), ",".join(RUNS))
    units = {}
    for r in rows:
        units.setdefault((r["run_id"], r["judge_group"], r["repeat"]), {}).setdefault(r["pair_id"], {}).setdefault(r["version"], []).append(r["rating"])
    gap = gaps_from(units, list(units))
    assert set(gap) == set(obs) and all(abs(gap[p] - float(obs[p]["effect"])) < 0.006 for p in obs), "gaps differ from out/round2b_pooled"
    se = {p: (float(obs[p]["ci_high"]) - float(obs[p]["ci_low"])) / (2 * 1.96) for p in obs}
    pred, reason = {}, {}
    for m in MODELS:
        if not prov.get("points:" + m, {}).get("usable"):
            raise SystemExit("no usable predictions from %s" % m)
        a = json.load(open(os.path.join(args.answers, m + ".json")))["predictions"]
        codes = man["models"][m]
        assert sorted(x["pair"] for x in a) == sorted(codes), m
        pred[m] = {codes[x["pair"]]: float(x["gap"]) for x in a}
        reason[m] = {codes[x["pair"]]: x.get("reason", "") for x in a}
    authored = [p for p in pairs if pairs[p]["pair_type"] == "authored"]
    own = {m: sorted(p for p in authored if pairs[p]["author"]["tier"] == m) for m in MODELS}
    allp = sorted(pairs)

    def mae(m, ids, g=gap):
        return statistics.mean(abs(pred[m][p] - g[p]) for p in ids)

    def pscore(m, ids, g=gap):
        return statistics.mean(max(0.0, 1 - abs(pred[m][p] - g[p]) / SCALE) for p in ids)

    def classmid(p):
        pr = pairs[p]["prediction"]
        mag = {"none": 0.0, "small": 1.0, "large": 2.0}[pr["size"]]
        return mag if pr["direction"] == "A_higher" else (-mag if pr["direction"] == "B_higher" else 0.0)

    res = {"design": "see the docstring of pipeline/round2/point_predictions.py (committed before collection)", "authors": {}, "predictors_all_items": {}}
    floor_own = {m: statistics.mean(se[p] * math.sqrt(2 / math.pi) for p in own[m]) for m in MODELS}
    for m in MODELS:
        res["authors"][m] = {
            "own_pairs_mae": round(mae(m, own[m]), 3),
            "own_pairs_point_score": round(pscore(m, own[m]), 3),
            "own_pairs_mean_signed_error": round(statistics.mean(pred[m][p] - gap[p] for p in own[m]), 3),
            "class_midpoint_baseline_mae": round(statistics.mean(abs(classmid(p) - gap[p]) for p in own[m]), 3),
            "noise_floor_mae": round(floor_own[m], 3),
            "by_factor_mae": {f: round(mae(m, [p for p in own[m] if pairs[p]["factor_id"] == f]), 3) for f in NEW},
            "pairs": {p: {"predicted": pred[m][p], "measured": round(gap[p], 2), "error": round(pred[m][p] - gap[p], 2),
                          "class_midpoint": classmid(p), "reason": reason[m][p]} for p in own[m]}}
        xs, ys = [pred[m][p] for p in allp], [gap[p] for p in allp]
        res["predictors_all_items"][m] = {"mae": round(mae(m, allp), 3), "point_score": round(pscore(m, allp), 3),
                                          "correlation": round(statistics.correlation(xs, ys), 3),
                                          "mean_signed_error": round(statistics.mean(x - y for x, y in zip(xs, ys)), 3),
                                          "mae_on_authored_27": round(mae(m, authored), 3)}
    res["noise_floor_all_items_mae"] = round(statistics.mean(se[p] * math.sqrt(2 / math.pi) for p in allp), 3)

    # judge-level resampling
    rng = random.Random(20261125)
    groups = sorted({u[1] for u in units})
    sims = []
    for _ in range(args.n_boot):
        keys = []
        for g in groups:
            pool = [u for u in units if u[1] == g]
            keys += rng.choices(pool, k=len(pool))
        # resampled units can repeat; gaps_from pools their ratings
        acc = {}
        for u in keys:
            for pid, vs in units[u].items():
                for v, xs in vs.items():
                    acc.setdefault(pid, {}).setdefault(u[1], {"A": [], "B": []})[v].extend(xs)
        g2 = {pid: statistics.mean(statistics.mean(c["A"]) - statistics.mean(c["B"]) for c in per.values()) for pid, per in acc.items()}
        sims.append({m: (mae(m, own[m], g2), mae(m, allp, g2)) for m in MODELS})
    def order(vals):
        return " < ".join(sorted(MODELS, key=lambda m: vals[m]))
    own_orders, all_orders = {}, {}
    for s in sims:
        k1, k2 = order({m: s[m][0] for m in MODELS}), order({m: s[m][1] for m in MODELS})
        own_orders[k1] = own_orders.get(k1, 0) + 1
        all_orders[k2] = all_orders.get(k2, 0) + 1
    n = len(sims)
    pair_share = {}
    for a, b in itertools.combinations(MODELS, 2):
        d0 = mae(a, own[a]) - mae(b, own[b])
        pair_share["%s vs %s" % (a, b)] = {
            "own_mae_difference": round(d0, 3),
            "same_sign_share": round(sum(1 for s in sims if (s[a][0] - s[b][0]) * d0 > 0) / n, 3) if d0 else None,
            "own_mae_sd": {a: round(statistics.pstdev(s[a][0] for s in sims), 3), b: round(statistics.pstdev(s[b][0] for s in sims), 3)}}
    res["judge_level_resampling"] = {"n": n, "own_pairs_order_by_mae": {k: round(v / n, 3) for k, v in sorted(own_orders.items(), key=lambda kv: -kv[1])},
                                     "all_items_order_by_mae": {k: round(v / n, 3) for k, v in sorted(all_orders.items(), key=lambda kv: -kv[1])},
                                     "pairs": pair_share}

    # permutation test on own-pair errors, authors shuffled within factor
    err = {p: abs(pred[pairs[p]["author"]["tier"]][p] - gap[p]) for p in authored}
    tier = {p: pairs[p]["author"]["tier"] for p in authored}
    perm = {}
    for a, b in itertools.combinations(MODELS, 2):
        ids = [p for p in authored if tier[p] in (a, b)]
        obs_d = statistics.mean(err[p] for p in ids if tier[p] == a) - statistics.mean(err[p] for p in ids if tier[p] == b)
        h = 0
        for _ in range(args.n_perm):
            lab = {}
            for f in NEW:
                fid = [p for p in ids if pairs[p]["factor_id"] == f]
                tt = [tier[p] for p in fid]
                rng.shuffle(tt)
                lab.update(zip(fid, tt))
            d = statistics.mean(err[p] for p in ids if lab[p] == a) - statistics.mean(err[p] for p in ids if lab[p] == b)
            h += abs(d) >= abs(obs_d) - 1e-12
        perm["%s vs %s" % (a, b)] = {"own_mae_difference": round(obs_d, 3), "permutation_p": round((h + 1) / (args.n_perm + 1), 4)}
    res["own_pairs_permutation"] = perm

    # paired sign-flip test on all 37 items
    paired = {}
    for a, b in itertools.combinations(MODELS, 2):
        d = [abs(pred[a][p] - gap[p]) - abs(pred[b][p] - gap[p]) for p in allp]
        obs_m = statistics.mean(d)
        h = sum(1 for _ in range(args.n_perm) if abs(statistics.mean(x if rng.random() < 0.5 else -x for x in d)) >= abs(obs_m) - 1e-12)
        paired["%s vs %s" % (a, b)] = {"mean_error_difference": round(obs_m, 3), "sign_flip_p": round((h + 1) / (args.n_perm + 1), 4)}
    res["all_items_paired"] = paired

    so = res["judge_level_resampling"]["pairs"]["sonnet vs opus"]
    res["pass_mark"] = {"rule": "own-pair MAE of Sonnet and Opus differ in the same direction in >= 90% of judge-level resamples AND permutation p < 0.05",
                        "same_sign_share": so["same_sign_share"], "permutation_p": perm["sonnet vs opus"]["permutation_p"],
                        "separates": bool(so["same_sign_share"] is not None and so["same_sign_share"] >= 0.9 and perm["sonnet vs opus"]["permutation_p"] < 0.05)}
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)

    for m in MODELS:
        a = res["authors"][m]
        print("%-7s own 9: MAE %.2f  point score %.2f  signed %+.2f  | class-midpoint MAE %.2f  noise floor %.2f  | by factor %s" % (
            m, a["own_pairs_mae"], a["own_pairs_point_score"], a["own_pairs_mean_signed_error"], a["class_midpoint_baseline_mae"],
            a["noise_floor_mae"], a["by_factor_mae"]))
    for m in MODELS:
        x = res["predictors_all_items"][m]
        print("%-7s all 37: MAE %.2f  r %.2f  signed %+.2f  authored-27 MAE %.2f" % (m, x["mae"], x["correlation"], x["mean_signed_error"], x["mae_on_authored_27"]))
    print("noise floor, all items: %.2f" % res["noise_floor_all_items_mae"])
    print("judge-level own order:", json.dumps(res["judge_level_resampling"]["own_pairs_order_by_mae"]))
    print("judge-level all order:", json.dumps(res["judge_level_resampling"]["all_items_order_by_mae"]))
    print("pairs:", json.dumps(res["judge_level_resampling"]["pairs"]))
    print("permutation:", json.dumps(perm))
    print("paired all items:", json.dumps(paired))
    print("pass mark:", json.dumps(res["pass_mark"]))
    print("wrote", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["build", "check", "analyse"])
    ap.add_argument("--out")
    ap.add_argument("--transcripts")
    ap.add_argument("--answers", default=ANS)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--n-perm", type=int, default=20000)
    a = ap.parse_args()
    {"build": build, "check": check, "analyse": analyse}[a.step](a)
