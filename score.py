#!/usr/bin/env python3
"""Thought-experiment authoring: scoring script.

Reruns every number from the data files:

    python3 score.py                      # vignettes.json + judgments.csv (+ audits.csv)
    python3 score.py --run main --boot 10000

Standard library only. Writes out/pair_scores.csv, out/author_summary.csv,
out/results.json and (if report.py is present) results.html.

The scoring rules are the RULES constant below. They were fixed before any
judgment was collected.
"""
import argparse, csv, difflib, json, math, os, random, re, statistics, zlib
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))

RULES = {
    # Effect = mean rating of version A minus mean rating of version B, in scale points,
    # computed inside each judge group and then averaged across groups (equal weight per group).
    "none_below": 0.5,           # |effect| < 0.5            -> size "none"
    "large_from": 1.5,           # |effect| >= 1.5           -> size "large"; in between "small"
    "ci_level": 0.95,            # percentile bootstrap, resampling ratings inside each group x version cell
    "group_agreement": 0.75,     # share of judge groups whose own effect must have the same sign
    "weights": {"prediction": 0.40, "confounds": 0.25, "originality": 0.20, "comprehension": 0.15},
    # Prediction score ("distance" rule, from 22 November 2026): credit falls with the distance between the measured
    # gap and the range the prediction names (none: under 0.5 either way; small: 0.5 to 1.5; large: 1.5 or more),
    # reaching 0 at distance_scale points; and a pair that is supposed to show a gap (authored pairs, classic controls)
    # earns nothing unless its gap is confirmed in the predicted direction. The earlier rule ("classes": half for
    # direction, half for the size class) rewarded predicting "no difference" whenever effects were small.
    "prediction_rule": "distance",
    "distance_scale": 1.5,
    "demonstration_required": ["authored", "control_classic"],
    "comprehension_floor": 0.80, # below this a pair is flagged as not understood
    "format_cap": 50.0,          # a pair that breaks a hard format rule cannot score above this
}
SIZE_ORDER = {"none": 0, "small": 1, "large": 2}


# ----------------------------------------------------------------------------- loading

def load_judgments(path, run):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if run and r["run_id"] not in run.split(","):
                continue
            r["rating"] = int(r["rating"])
            r["position"] = int(r["position"]) if r.get("position") else None
            rows.append(r)
    return rows


def load_audits(path, run):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if run and r["run_id"] not in run.split(","):
                continue
            r["confound_severity"] = int(r["confound_severity"])
            r["originality"] = int(r["originality"])
            r["comprehension_key_ok"] = r["comprehension_key_ok"].strip().lower() in ("1", "true", "yes")
            r["other_differences"] = [s for s in r["other_differences"].split(" || ") if s.strip()]
            rows.append(r)
    return rows


# ----------------------------------------------------------------------------- statistics

def mean(xs):
    return sum(xs) / len(xs)


def pct(sorted_xs, q):
    if not sorted_xs:
        return None
    k = (len(sorted_xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return sorted_xs[lo] + (sorted_xs[hi] - sorted_xs[lo]) * (k - lo)


def cliffs_delta(a, b):
    gt = sum(1 for x in a for y in b if x > y)
    lt = sum(1 for x in a for y in b if x < y)
    return (gt - lt) / (len(a) * len(b))


def effect_stats(cell, n_boot, rng):
    """cell: {version: {group: [ratings]}} for one pair."""
    groups = sorted(g for g in cell["A"] if g in cell["B"] and cell["A"][g] and cell["B"][g])
    if not groups:
        return None
    per_group = {}
    for g in groups:
        a, b = cell["A"][g], cell["B"][g]
        per_group[g] = {"n_a": len(a), "n_b": len(b), "mean_a": mean(a), "mean_b": mean(b),
                        "effect": mean(a) - mean(b), "cliffs_delta": cliffs_delta(a, b),
                        "ratings_a": a, "ratings_b": b}
    G = len(groups)
    delta = mean([per_group[g]["effect"] for g in groups])
    min_n = min(min(per_group[g]["n_a"], per_group[g]["n_b"]) for g in groups)
    boots = []
    if min_n >= 2:
        method = "stratified: ratings resampled inside each judge-group x version cell"
        A = [cell["A"][g] for g in groups]
        B = [cell["B"][g] for g in groups]
        for _ in range(n_boot):
            tot = 0.0
            for a, b in zip(A, B):
                tot += mean(rng.choices(a, k=len(a))) - mean(rng.choices(b, k=len(b)))
            boots.append(tot / G)
    else:
        method = "fallback: judge groups resampled (fewer than 2 ratings per cell)"
        effs = [per_group[g]["effect"] for g in groups]
        for _ in range(n_boot):
            boots.append(mean(rng.choices(effs, k=G)))
    boots.sort()
    alpha = (1 - RULES["ci_level"]) / 2
    lo, hi = pct(boots, alpha), pct(boots, 1 - alpha)
    # Sensitivity only: an interval that also resamples the judge groups themselves, so that
    # disagreement between models (not just repeat-to-repeat noise) widens it. Not used for scoring.
    boots2 = []
    for _ in range(n_boot):
        tot = 0.0
        for g in rng.choices(groups, k=G):
            a, b = cell["A"][g], cell["B"][g]
            tot += mean(rng.choices(a, k=len(a))) - mean(rng.choices(b, k=len(b)))
        boots2.append(tot / G)
    boots2.sort()
    lo2, hi2 = pct(boots2, alpha), pct(boots2, 1 - alpha)
    variances = []
    for g in groups:
        for v in ("ratings_a", "ratings_b"):
            xs = per_group[g][v]
            if len(xs) >= 2:
                variances.append(statistics.variance(xs))
    sd = math.sqrt(mean(variances)) if variances else None
    same_sign = sum(1 for g in groups if delta != 0 and per_group[g]["effect"] * delta > 0)
    return {
        "groups": groups, "per_group": per_group,
        "n_a": sum(per_group[g]["n_a"] for g in groups), "n_b": sum(per_group[g]["n_b"] for g in groups),
        "mean_a": mean([per_group[g]["mean_a"] for g in groups]),
        "mean_b": mean([per_group[g]["mean_b"] for g in groups]),
        "effect": delta, "ci_low": lo, "ci_high": hi, "ci_method": method,
        "ci_model_level_low": lo2, "ci_model_level_high": hi2,
        "cliffs_delta": mean([per_group[g]["cliffs_delta"] for g in groups]),
        "within_cell_sd": sd,
        "std_effect": (delta / sd) if sd else None,
        "groups_same_sign": same_sign, "groups_total": G,
    }


def classify(es):
    """Observed result of a pair -> direction and size, by the pre-set rules."""
    d = es["effect"]
    ad = abs(d)
    size = "none" if ad < RULES["none_below"] else ("large" if ad >= RULES["large_from"] else "small")
    ci_excludes_zero = es["ci_low"] > 0 or es["ci_high"] < 0
    need = math.ceil(RULES["group_agreement"] * es["groups_total"])
    groups_agree = es["groups_same_sign"] >= need
    if size == "none":
        direction = "none"
    elif ci_excludes_zero and groups_agree:
        direction = "A_higher" if d > 0 else "B_higher"
    else:
        direction = "unclear"
    return {"direction": direction, "size": size, "ci_excludes_zero": ci_excludes_zero,
            "groups_agree": groups_agree,
            "equivalence_supported": es["ci_low"] > -RULES["none_below"] and es["ci_high"] < RULES["none_below"]}


def prediction_score(pred, obs, effect):
    """0..1. Half for direction, half for size (exact bin 1, adjacent bin 0.5). Opposite direction scores 0."""
    direction_hit = pred["direction"] == obs["direction"]
    size_gap = abs(SIZE_ORDER[pred["size"]] - SIZE_ORDER[obs["size"]])
    size_part = {0: 1.0, 1: 0.5, 2: 0.0}[size_gap]
    opposite = (pred["direction"] in ("A_higher", "B_higher") and obs["size"] != "none"
                and ((effect > 0) != (pred["direction"] == "A_higher")))
    score = 0.0 if opposite else 0.5 * (1.0 if direction_hit else 0.0) + 0.5 * size_part
    return {"score": score, "direction_hit": direction_hit, "size_hit": size_gap == 0, "opposite": opposite}


def predicted_range(pred):
    """The range of A-minus-B gaps (1-7 scale) that a direction-and-size prediction names."""
    lo, hi = RULES["none_below"], RULES["large_from"]
    if pred["direction"] == "none":
        return (-lo, lo)
    r = (lo, hi) if pred["size"] == "small" else (hi, 6.0)
    return r if pred["direction"] == "A_higher" else (-r[1], -r[0])


def prediction_score_distance(pred, obs, effect, pair_type):
    """0..1. 1 - distance/scale, where distance is how far the measured gap lies outside the predicted range; 0 for a
    pair that should show a gap (RULES['demonstration_required']) but has no confirmed gap in the predicted direction."""
    lo, hi = predicted_range(pred)
    distance = 0.0 if lo <= effect <= hi else min(abs(effect - lo), abs(effect - hi))
    accuracy = max(0.0, 1.0 - distance / RULES["distance_scale"])
    required = pair_type in RULES["demonstration_required"]
    demonstrated = pred["direction"] in ("A_higher", "B_higher") and obs["direction"] == pred["direction"]
    return {"score": accuracy if (demonstrated or not required) else 0.0, "accuracy": accuracy, "distance": distance,
            "demonstration_required": required, "demonstrated": demonstrated}


# ----------------------------------------------------------------------------- text measures

def text_metrics(a_text, b_text):
    a, b = a_text.split(), b_text.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    changed = sum(max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal")
    return {"words_a": len(a), "words_b": len(b), "length_gap": abs(len(a) - len(b)),
            "words_changed": changed, "share_changed": changed / max(len(a), len(b))}


STOP = set("""about above after again against also another because been before being below between both could does doing
down during each from further have having here himself herself into itself just more most much only other over same
should some such than that their theirs them then there these they this those through under until very were what when
where which while will with would your yours once every still even back onto never always asked says said knew know
knows want wanted wants goes went came come that's didn't does not""".split())


def content_words(text):
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP}


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


# ----------------------------------------------------------------------------- audits

def upper_median(xs):
    s = sorted(xs)
    return s[len(s) // 2]


def lower_median(xs):
    s = sorted(xs)
    return s[(len(s) - 1) // 2]


def aggregate_audits(rows):
    if not rows:
        return None
    sev = [r["confound_severity"] for r in rows]
    orig = [r["originality"] for r in rows]
    realized = [r["factor_realized"] for r in rows]
    return {
        "n_auditors": len(rows),
        "confound_severity": upper_median(sev), "confound_severity_all": sev,
        "originality": lower_median(orig), "originality_all": orig,
        "factor_realized_all": realized,
        "factor_not_realized": realized.count("no") * 2 >= len(realized),
        "factor_realized_yes_share": realized.count("yes") / len(realized),
        "key_ok_share": sum(1 for r in rows if r["comprehension_key_ok"]) / len(rows),
        "detail": [{"auditor": r["auditor_group"], "factor_realized": r["factor_realized"],
                    "confound_severity": r["confound_severity"], "originality": r["originality"],
                    "closest_known_case": r["closest_known_case"], "other_differences": r["other_differences"],
                    "question_problems": r["question_problems"], "comprehension_key_ok": r["comprehension_key_ok"]}
                   for r in rows],
    }


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vignettes", default=os.path.join(ROOT, "vignettes.json"))
    ap.add_argument("--judgments", default=os.path.join(ROOT, "judgments.csv"))
    ap.add_argument("--audits", default=os.path.join(ROOT, "audits.csv"))
    ap.add_argument("--run", default="main", help="run_id to score; several separated by commas (empty string = all rows)")
    ap.add_argument("--audit-run", help="run_id of the audits to use (default: the same as --run), e.g. to score another "
                                        "vendor's judges against the pilot's confound and originality audits")
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(ROOT, "out"))
    ap.add_argument("--no-report", action="store_true")
    ap.add_argument("--prediction-rule", choices=["distance", "classes"], default=RULES["prediction_rule"],
                    help="distance: the current rule; classes: the pilot's original rule (half direction, half size class)")
    args = ap.parse_args()
    RULES["prediction_rule"] = args.prediction_rule

    doc = json.load(open(args.vignettes, encoding="utf-8"))
    pairs = doc["pairs"]
    calib = doc.get("audit_calibration_pairs", [])
    J = load_judgments(args.judgments, args.run)
    AU = load_audits(args.audits, args.run if args.audit_run is None else args.audit_run)
    if not J:
        raise SystemExit("no judgments for run_id=%r in %s" % (args.run, args.judgments))
    os.makedirs(args.out, exist_ok=True)

    # ---- data checks
    cells = defaultdict(lambda: {"A": defaultdict(list), "B": defaultdict(list)})
    comp = defaultdict(lambda: {"A": [], "B": []})
    seen_versions = defaultdict(set)
    cells_ok = defaultdict(lambda: {"A": defaultdict(list), "B": defaultdict(list)})
    key = {p["pair_id"]: p["comprehension_question"]["correct"] for p in pairs}
    problems = []
    for r in J:
        if r["pair_id"] not in key:
            problems.append("unknown pair_id %s" % r["pair_id"]); continue
        if not 1 <= r["rating"] <= 7:
            problems.append("rating out of range in %s" % r["judge_id"]); continue
        cells[r["pair_id"]][r["version"]][r["judge_group"]].append(r["rating"])
        ok = r["comprehension_answer"].strip().lower() == key[r["pair_id"]][r["version"]]
        r["_comp_ok"] = ok
        if ok:
            cells_ok[r["pair_id"]][r["version"]][r["judge_group"]].append(r["rating"])
        comp[r["pair_id"]][r["version"]].append((r["judge_group"], ok))
        seen_versions[(r["judge_id"], r["pair_id"])].add(r["version"])
    both = [k for k, v in seen_versions.items() if len(v) > 1]
    if both:
        problems.append("%d judge(s) saw both versions of a pair, e.g. %s" % (len(both), both[0]))
    groups_all = sorted({r["judge_group"] for r in J})
    judges_all = sorted({r["judge_id"] for r in J})

    aud_by_pair = defaultdict(list)
    for r in AU:
        aud_by_pair[r["pair_id"]].append(r)

    # ---- lexical convergence between pairs (diagnostic only)
    words = {p["pair_id"]: content_words(p["versions"]["A"]["text"] + " " + p["versions"]["B"]["text"]) for p in pairs}
    nearest = {}
    for p in pairs:
        best = (0.0, None)
        for q in pairs:
            if q["pair_id"] == p["pair_id"] or q["author"]["author_id"] == p["author"]["author_id"]:
                continue
            s = jaccard(words[p["pair_id"]], words[q["pair_id"]])
            if s > best[0]:
                best = (s, q["pair_id"])
        nearest[p["pair_id"]] = {"pair_id": best[1], "similarity": round(best[0], 3)}

    # ---- builder's annotations (flags only; never change a score)
    convergence = {}
    apath = os.path.join(ROOT, "annotations.json")
    if os.path.exists(apath):
        for c in json.load(open(apath, encoding="utf-8")).get("convergence", []):
            for pid in c["pairs"]:
                convergence[pid] = {"label": c["label"], "with": [x for x in c["pairs"] if x != pid]}

    # ---- per pair
    W = RULES["weights"]
    out_pairs = []
    for p in pairs:
        pid = p["pair_id"]
        rng = random.Random(zlib.crc32(("%d|%s" % (args.seed, pid)).encode()))
        es = effect_stats(cells[pid], args.boot, rng)
        rec = {"pair_id": pid, "pair_type": p["pair_type"], "factor_id": p["factor_id"],
               "author_id": p["author"]["author_id"], "author_tier": p["author"].get("tier", ""),
               "author_type": p["author"]["type"], "title": p["title"],
               "versions": p["versions"], "judgment_question": p["judgment_question"],
               "comprehension_question": p["comprehension_question"],
               "intended_difference": p["intended_difference"], "prediction": p.get("prediction"),
               "reference": p.get("reference"), "null_detail": p.get("null_detail"),
               "originality_note": p.get("originality_note"),
               "format_problems": p.get("format_problems", []),
               "text": text_metrics(p["versions"]["A"]["text"], p["versions"]["B"]["text"]),
               "nearest_pair": nearest[pid]}
        if es is None:
            rec["error"] = "no complete judgments"
            out_pairs.append(rec); continue
        obs = classify(es)
        rec["effect"] = es
        ok_groups = [g for g in cells_ok[pid]["A"] if cells_ok[pid]["A"][g] and cells_ok[pid]["B"].get(g)]
        n_kept = sum(len(cells_ok[pid][v][g]) for v in ("A", "B") for g in cells_ok[pid][v])
        rec["effect_if_comprehension_passed"] = {
            "effect": mean([mean(cells_ok[pid]["A"][g]) - mean(cells_ok[pid]["B"][g]) for g in ok_groups]) if ok_groups else None,
            "n_excluded": es["n_a"] + es["n_b"] - n_kept}
        rec["observed"] = obs
        c_all = comp[pid]["A"] + comp[pid]["B"]
        rec["comprehension"] = {
            "accuracy": mean([1.0 if ok else 0.0 for _, ok in c_all]),
            "accuracy_a": mean([1.0 if ok else 0.0 for _, ok in comp[pid]["A"]]),
            "accuracy_b": mean([1.0 if ok else 0.0 for _, ok in comp[pid]["B"]]),
            "by_group": {g: mean([1.0 if ok else 0.0 for gg, ok in c_all if gg == g]) for g in groups_all},
        }
        ps = prediction_score(p["prediction"], obs, es["effect"]) if p.get("prediction") else None
        pd = prediction_score_distance(p["prediction"], obs, es["effect"], p["pair_type"]) if p.get("prediction") else None
        rec["prediction_result"] = ps
        rec["prediction_distance"] = pd
        aud = aggregate_audits(aud_by_pair.get(pid, []))
        rec["audit"] = aud
        flags = []
        main_ps = (pd if RULES["prediction_rule"] == "distance" else ps)
        comps = {"prediction": main_ps["score"] if main_ps else None, "comprehension": rec["comprehension"]["accuracy"],
                 "confounds": None, "originality": None}
        rec["prediction_scores_by_rule"] = {"distance": pd["score"] if pd else None, "classes": ps["score"] if ps else None}
        if aud:
            comps["confounds"] = 1 - aud["confound_severity"] / 3
            comps["originality"] = aud["originality"] / 3
            if aud["factor_not_realized"]:
                comps["prediction"] = 0.0
                flags.append("factor not realized (prediction component voided)")
            if aud["confound_severity"] == 3:
                flags.append("severe confound")
            if aud["originality"] == 0:
                flags.append("re-skin of a known case")
            if aud["key_ok_share"] < 0.5:
                flags.append("auditors dispute the comprehension key")
        if rec["comprehension"]["accuracy"] < RULES["comprehension_floor"]:
            flags.append("low comprehension")
        if obs["direction"] == "unclear":
            flags.append("gap not confirmed (interval includes 0 or judge groups disagree)")
        if es["groups_same_sign"] < es["groups_total"] and obs["size"] != "none":
            flags.append("not every judge model shows the gap")
        if min(es["mean_a"], es["mean_b"]) >= 6.5 or max(es["mean_a"], es["mean_b"]) <= 1.5:
            flags.append("both versions at the scale's ceiling or floor")
        if ps and ps["opposite"]:
            flags.append("gap opposite to prediction")
        if rec["format_problems"]:
            flags.append("format rule broken: " + "; ".join(rec["format_problems"]))
        if pid in convergence:
            rec["convergence"] = convergence[pid]
            flags.append("same setting as another pair (%s)" % convergence[pid]["label"])
        composite = None
        if all(comps[k] is not None for k in W):
            composite = 100 * sum(W[k] * comps[k] for k in W)
            if rec["format_problems"]:
                composite = min(composite, RULES["format_cap"])
        rec["components"] = comps
        rec["composite"] = composite
        if aud and comps["prediction"] is not None:
            shared = pid in convergence
            g_conf = aud["confound_severity"] <= 1 and not aud["factor_not_realized"]
            g_orig = aud["originality"] >= 1 and not shared
            rec["gated"] = {
                "behavior_score": 100 * (W["prediction"] * comps["prediction"] + W["comprehension"] * comps["comprehension"]) / (W["prediction"] + W["comprehension"]),
                "confound_gate": g_conf, "originality_gate": g_orig, "shared_setting": shared,
                "passes": g_conf and g_orig,
                "fails_on": [n for n, ok in (("confounds", g_conf), ("re-skin", aud["originality"] >= 1), ("shared setting", not shared)) if not ok]}
        rec["flags"] = flags
        rec["demonstrated"] = bool(ps and ps["direction_hit"] and p["prediction"]["direction"] != "none")
        out_pairs.append(rec)

    # ---- panel checks
    scored = [r for r in out_pairs if "effect" in r]
    classics = [r for r in scored if r["pair_type"] == "control_classic"]
    nulls = [r for r in scored if r["pair_type"] == "control_null"]
    authored = [r for r in scored if r["pair_type"] == "authored"]

    rng = random.Random(args.seed)
    noise = []
    for pid, cv in cells.items():
        for v in ("A", "B"):
            gs = [g for g in cv[v] if len(cv[v][g]) >= 2]
            if not gs:
                continue
            for _ in range(200):
                ds = []
                for g in gs:
                    xs = cv[v][g][:]
                    rng.shuffle(xs)
                    h = (len(xs) + 1) // 2
                    ds.append(mean(xs[:h]) - mean(xs[h:]))
                noise.append(abs(mean(ds)))
    noise.sort()

    cell_mean = {}
    for pid, cv in cells.items():
        for v in ("A", "B"):
            allr = [x for g in cv[v] for x in cv[v][g]]
            if allr:
                cell_mean[(pid, v)] = mean(allr)
    pos, res = [], []
    for r in J:
        if r["position"] is not None and (r["pair_id"], r["version"]) in cell_mean:
            pos.append(r["position"]); res.append(r["rating"] - cell_mean[(r["pair_id"], r["version"])])
    pos_r = None
    if len(pos) > 2 and statistics.pstdev(pos) > 0 and statistics.pstdev(res) > 0:
        mp, mr = mean(pos), mean(res)
        pos_r = sum((a - mp) * (b - mr) for a, b in zip(pos, res)) / (len(pos) * statistics.pstdev(pos) * statistics.pstdev(res))

    tier_diag = {}
    for g in groups_all:
        rs = [r for r in J if r["judge_group"] == g]
        sds = []
        for pid, cv in cells.items():
            for v in ("A", "B"):
                if len(cv[v].get(g, [])) >= 2:
                    sds.append(statistics.stdev(cv[v][g]))
        effs = [abs(r["effect"]["per_group"][g]["effect"]) for r in authored if g in r["effect"]["per_group"]]
        null_effs = [abs(r["effect"]["per_group"][g]["effect"]) for r in nulls if g in r["effect"]["per_group"]]
        tier_diag[g] = {
            "n_judgments": len(rs), "n_judges": len({r["judge_id"] for r in rs}),
            "mean_rating": mean([r["rating"] for r in rs]),
            "share_extreme": mean([1.0 if r["rating"] in (1, 7) else 0.0 for r in rs]),
            "mean_within_cell_sd": mean(sds) if sds else None,
            "share_cells_zero_variance": mean([1.0 if s == 0 else 0.0 for s in sds]) if sds else None,
            "comprehension_accuracy": mean([1.0 if r.get("_comp_ok") else 0.0 for r in rs]),
            "mean_abs_effect_authored": mean(effs) if effs else None,
            "mean_abs_effect_nulls": mean(null_effs) if null_effs else None,
            "nulls_half_point_or_more": sum(1 for x in null_effs if x >= RULES["none_below"]),
        }

    own = []
    for r in authored:
        pr = r["prediction"]
        if pr["direction"] == "none":
            continue
        sign = 1 if pr["direction"] == "A_higher" else -1
        g_own = r["author_id"]
        pg = r["effect"]["per_group"]
        if g_own in pg and len(pg) > 1:
            others = [pg[g]["effect"] * sign for g in pg if g != g_own]
            own.append({"pair_id": r["pair_id"], "author": g_own, "own": pg[g_own]["effect"] * sign, "others": mean(others)})

    auditors = sorted({r["auditor_group"] for r in AU})
    classic_ids = {p["pair_id"] for p in pairs if p["pair_type"] == "control_classic"}
    null_ids = {p["pair_id"] for p in pairs if p["pair_type"] == "control_null"}
    calib_ids = {p["pair_id"]: p for p in calib}
    auditor_checks = {}
    for a in auditors:
        rows = [r for r in AU if r["auditor_group"] == a]
        cl = [r for r in rows if r["pair_id"] in classic_ids]
        nl = [r for r in rows if r["pair_id"] in null_ids]
        ca = [r for r in rows if r["pair_id"] in calib_ids]
        named = 0
        for r in ca:
            kws = calib_ids[r["pair_id"]].get("planted_keywords", [])
            text = " ".join(r["other_differences"]).lower()
            if any(k.lower() in text for k in kws):
                named += 1
        au_rows = [r for r in rows if r["pair_id"].startswith("au_")]
        own_rows = [r for r in au_rows if ("anthropic/" + r["pair_id"].split("_")[1]) in a or r["pair_id"].split("_")[1] in a]
        other_rows = [r for r in au_rows if r not in own_rows]
        auditor_checks[a] = {
            "classics_flagged_as_known": sum(1 for r in cl if r["originality"] <= 1), "classics_total": len(cl),
            "planted_confounds_rated_2_plus": sum(1 for r in ca if r["confound_severity"] >= 2),
            "planted_confounds_named": named, "planted_total": len(ca),
            "null_pairs_rated_2_plus": sum(1 for r in nl if r["confound_severity"] >= 2), "nulls_total": len(nl),
            "mean_confound_severity_authored": mean([r["confound_severity"] for r in au_rows]) if au_rows else None,
            "mean_originality_authored": mean([r["originality"] for r in au_rows]) if au_rows else None,
            "own_tier_mean_severity": mean([r["confound_severity"] for r in own_rows]) if own_rows else None,
            "other_tier_mean_severity": mean([r["confound_severity"] for r in other_rows]) if other_rows else None,
            "own_tier_mean_originality": mean([r["originality"] for r in own_rows]) if own_rows else None,
            "other_tier_mean_originality": mean([r["originality"] for r in other_rows]) if other_rows else None,
        }
    calib_out = []
    for cid, cp in calib_ids.items():
        rows = aud_by_pair.get(cid, [])
        calib_out.append({"pair_id": cid, "planted_confound": cp.get("planted_confound"),
                          "severity_by_auditor": {r["auditor_group"]: r["confound_severity"] for r in rows},
                          "differences_by_auditor": {r["auditor_group"]: r["other_differences"] for r in rows}})

    # how much the auditors agree with each other on the authored pairs
    def agreement(field):
        diffs, exact, wide, n = [], 0, 0, 0
        for r in authored:
            vals = [x[field] for x in aud_by_pair.get(r["pair_id"], [])]
            if len(vals) < 2:
                continue
            n += 1
            wide += 1 if max(vals) - min(vals) >= 2 else 0
            for i in range(len(vals)):
                for j in range(i + 1, len(vals)):
                    diffs.append(abs(vals[i] - vals[j]))
                    exact += 1 if vals[i] == vals[j] else 0
        if not diffs:
            return None
        return {"mean_abs_difference": mean(diffs), "exact_agreement": exact / len(diffs),
                "share_of_pairs_two_or_more_apart": wide / n, "n_pairs": n}
    auditor_agreement = {"confound_severity": agreement("confound_severity"), "originality": agreement("originality")}
    by_author = {}
    for a in auditors:
        by_author[a] = {}
        for tier in sorted({r["author_tier"] for r in authored}):
            rows = [x for r in authored if r["author_tier"] == tier for x in aud_by_pair.get(r["pair_id"], []) if x["auditor_group"] == a]
            if rows:
                by_author[a][tier] = {"confound_severity": mean([x["confound_severity"] for x in rows]),
                                      "originality": mean([x["originality"] for x in rows])}
    # would any verdict change under the wider, model-level interval?
    changed = []
    for r in scored:
        e, ob = r["effect"], r["observed"]
        excl2 = e["ci_model_level_low"] > 0 or e["ci_model_level_high"] < 0
        if ob["size"] != "none" and ob["direction"] in ("A_higher", "B_higher") and not excl2:
            changed.append(r["pair_id"])
    null_excl2 = sum(1 for r in nulls if r["effect"]["ci_model_level_low"] > 0 or r["effect"]["ci_model_level_high"] < 0)
    own_diffs = [o["own"] - o["others"] for o in own]
    own_ci = None
    if own_diffs:
        bs = sorted(mean(rng.choices(own_diffs, k=len(own_diffs))) for _ in range(5000))
        own_ci = [pct(bs, 0.025), pct(bs, 0.975)]

    panel = {
        "auditor_agreement": auditor_agreement, "auditor_by_author": by_author,
        "model_level_interval": {"gaps_no_longer_confirmed": changed, "nulls_excluding_zero": null_excl2},
        "classics": [{"pair_id": r["pair_id"], "expected": r["prediction"], "effect": r["effect"]["effect"],
                      "ci": [r["effect"]["ci_low"], r["effect"]["ci_high"]], "observed": r["observed"],
                      "reproduced": r["observed"]["direction"] == r["prediction"]["direction"]} for r in classics],
        "classics_reproduced": sum(1 for r in classics if r["observed"]["direction"] == r["prediction"]["direction"]),
        "classics_total": len(classics),
        "nulls": [{"pair_id": r["pair_id"], "effect": r["effect"]["effect"],
                   "ci": [r["effect"]["ci_low"], r["effect"]["ci_high"]], "observed": r["observed"]} for r in nulls],
        "null_false_positives": sum(1 for r in nulls if r["observed"]["direction"] in ("A_higher", "B_higher")),
        "null_ci_excludes_zero": sum(1 for r in nulls if r["observed"]["ci_excludes_zero"]),
        "null_max_abs_effect": max([abs(r["effect"]["effect"]) for r in nulls]) if nulls else None,
        "nulls_total": len(nulls),
        "split_half_noise": {"median": pct(noise, 0.5), "p95": pct(noise, 0.95),
                             "share_at_least_half_point": mean([1.0 if x >= RULES["none_below"] else 0.0 for x in noise]) if noise else None,
                             "n": len(noise)},
        "position_effect_r": pos_r,
        "by_group": tier_diag,
        "own_tier": {"pairs": own,
                     "mean_own": mean([o["own"] for o in own]) if own else None,
                     "mean_others": mean([o["others"] for o in own]) if own else None,
                     "n_own_larger": sum(1 for d in own_diffs if d > 0), "mean_difference_ci": own_ci},
        "auditors": auditor_checks,
        "audit_calibration": calib_out,
    }

    # ---- author summary
    authors = []
    for aid in sorted({r["author_id"] for r in authored}):
        rs = [r for r in authored if r["author_id"] == aid]
        comp_ok = [r for r in rs if r["composite"] is not None]
        authors.append({
            "author_id": aid, "tier": rs[0]["author_tier"], "n_pairs": len(rs),
            "mean_composite": mean([r["composite"] for r in comp_ok]) if comp_ok else None,
            "direction_hits": sum(1 for r in rs if r["prediction_result"]["direction_hit"]),
            "size_hits": sum(1 for r in rs if r["prediction_result"]["size_hit"]),
            "full_hits": sum(1 for r in rs if r["prediction_result"]["direction_hit"] and r["prediction_result"]["size_hit"]),
            "demonstrated": sum(1 for r in rs if r["demonstrated"]),
            "mean_prediction_score": mean([r["components"]["prediction"] for r in rs]),
            "mean_prediction_score_classes_rule": mean([0.0 if (r["audit"] or {}).get("factor_not_realized") else r["prediction_scores_by_rule"]["classes"] for r in rs]),
            "mean_abs_effect": mean([abs(r["effect"]["effect"]) for r in rs]),
            "mean_confound_severity": mean([r["audit"]["confound_severity"] for r in rs if r["audit"]]) if any(r["audit"] for r in rs) else None,
            "mean_originality": mean([r["audit"]["originality"] for r in rs if r["audit"]]) if any(r["audit"] for r in rs) else None,
            "mean_comprehension": mean([r["comprehension"]["accuracy"] for r in rs]),
            "mean_words_changed": mean([r["text"]["words_changed"] for r in rs]),
            "n_flagged": sum(1 for r in rs if r["flags"]),
            "gated_passes": sum(1 for r in rs if r.get("gated", {}).get("passes")),
            "gated_mean_behavior_of_passing": (mean([r["gated"]["behavior_score"] for r in rs if r.get("gated", {}).get("passes")])
                                               if any(r.get("gated", {}).get("passes") for r in rs) else None),
            "n_shared_setting": sum(1 for r in rs if r.get("convergence")),
        })

    results = {
        "benchmark": doc["benchmark"], "release": doc["release"], "run_id": args.run,
        "rules": RULES, "bootstrap": {"resamples": args.boot, "seed": args.seed},
        "data": {"n_judgments": len(J), "n_judges": len(judges_all), "judge_groups": groups_all,
                 "n_pairs": len(pairs), "n_audit_rows": len(AU), "auditors": auditors,
                 "min_ratings_per_cell": min(min(len(cv[v][g]) for g in cv[v]) for cv in cells.values() for v in ("A", "B") if cv[v]),
                 "problems": problems},
        "factors": doc["factors"], "pairs": out_pairs, "panel": panel, "authors": authors,
    }
    json.dump(results, open(os.path.join(args.out, "results.json"), "w"), indent=1, ensure_ascii=False)

    cols = ["pair_id", "pair_type", "factor_id", "author_tier", "title", "predicted_direction", "predicted_size",
            "n_a", "n_b", "mean_a", "mean_b", "effect", "ci_low", "ci_high", "cliffs_delta", "std_effect",
            "groups_same_sign", "groups_total", "observed_direction", "observed_size", "direction_hit", "size_hit",
            "prediction_score", "confound_severity", "originality", "comprehension", "words_changed",
            "share_changed", "composite", "flags", "gated_behavior_score", "gated_passes", "gated_fails_on",
            "prediction_rule", "distance_to_predicted_range", "gap_demonstrated", "prediction_score_classes_rule"]
    with open(os.path.join(args.out, "pair_scores.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in scored:
            e, pr, ps, au = r["effect"], r["prediction"] or {}, r["prediction_result"] or {}, r["audit"] or {}
            fmt = lambda x, n=2: "" if x is None else round(x, n)
            w.writerow([r["pair_id"], r["pair_type"], r["factor_id"], r["author_tier"], r["title"],
                        pr.get("direction", ""), pr.get("size", ""), e["n_a"], e["n_b"], fmt(e["mean_a"]), fmt(e["mean_b"]),
                        fmt(e["effect"]), fmt(e["ci_low"]), fmt(e["ci_high"]), fmt(e["cliffs_delta"]), fmt(e["std_effect"]),
                        e["groups_same_sign"], e["groups_total"], r["observed"]["direction"], r["observed"]["size"],
                        ps.get("direction_hit", ""), ps.get("size_hit", ""), fmt(r["components"]["prediction"]),
                        au.get("confound_severity", ""), au.get("originality", ""), fmt(r["comprehension"]["accuracy"], 3),
                        r["text"]["words_changed"], fmt(r["text"]["share_changed"], 3), fmt(r["composite"], 1),
                        " | ".join(r["flags"]), fmt((r.get("gated") or {}).get("behavior_score"), 1),
                        (r.get("gated") or {}).get("passes", ""), "; ".join((r.get("gated") or {}).get("fails_on", [])),
                        RULES["prediction_rule"], fmt((r.get("prediction_distance") or {}).get("distance")),
                        (r.get("prediction_distance") or {}).get("demonstrated", ""),
                        fmt(None if not r.get("prediction_scores_by_rule") else
                            (0.0 if au.get("factor_not_realized") else r["prediction_scores_by_rule"]["classes"]))])
    with open(os.path.join(args.out, "author_summary.csv"), "w", newline="", encoding="utf-8") as f:
        if authors:
            w = csv.DictWriter(f, fieldnames=list(authors[0].keys()))
            w.writeheader()
            for a in authors:
                w.writerow({k: (round(v, 3) if isinstance(v, float) else v) for k, v in a.items()})

    # ---- console summary
    print("run %r: %d judgments, %d judges, %d groups, min %d rating(s) per cell" % (
        args.run, len(J), len(judges_all), len(groups_all), results["data"]["min_ratings_per_cell"]))
    for pr in problems:
        print("  DATA PROBLEM:", pr)
    print("classic controls reproduced: %d/%d | null false positives: %d/%d (interval excludes 0: %d) | max |null effect| %.2f" % (
        panel["classics_reproduced"], panel["classics_total"], panel["null_false_positives"], panel["nulls_total"],
        panel["null_ci_excludes_zero"], panel["null_max_abs_effect"] or 0))
    if noise:
        print("split-half noise: median %.2f, 95th percentile %.2f" % (panel["split_half_noise"]["median"], panel["split_half_noise"]["p95"]))
    print("%-28s %-9s %6s %15s %5s %-9s %-6s %5s %4s %4s %5s %6s" % (
        "pair", "predicted", "effect", "95% interval", "grps", "observed", "size", "pred", "conf", "orig", "comp", "score"))
    for r in scored:
        e, pr, au = r["effect"], r["prediction"] or {}, r["audit"] or {}
        print("%-28s %-9s %+6.2f [%+5.2f, %+5.2f] %d/%d   %-9s %-6s %5s %4s %4s %5.2f %6s" % (
            r["pair_id"], (pr.get("direction", "")[:1] + "/" + pr.get("size", "")), e["effect"], e["ci_low"], e["ci_high"],
            e["groups_same_sign"], e["groups_total"], r["observed"]["direction"], r["observed"]["size"],
            "" if r["components"]["prediction"] is None else "%.2f" % r["components"]["prediction"],
            au.get("confound_severity", ""), au.get("originality", ""), r["comprehension"]["accuracy"],
            "" if r["composite"] is None else "%.1f" % r["composite"]))
    print("wrote", os.path.join(args.out, "results.json"), "pair_scores.csv", "author_summary.csv")

    if not args.no_report:
        try:
            import report
        except ImportError:
            return
        report.build(results, ROOT)


if __name__ == "__main__":
    main()
