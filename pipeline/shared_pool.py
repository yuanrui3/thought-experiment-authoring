#!/usr/bin/env python3
"""Shared-pool prediction score: every author predicts the measured gap of every item in a round, in points.

    python3 pipeline/shared_pool.py build --vignettes V --models haiku sonnet opus fable --tag T --out DIR --manifest M
    python3 pipeline/shared_pool.py check --tag T --transcripts DIR --out PROVENANCE.json
    python3 pipeline/shared_pool.py score --vignettes V --runs R1[,R2] --manifest M --answers DIR --provenance P --out NUMBERS.json

Adopted 24-25 November 2026 (owner's decision, "option B"), and committed before any prediction for the next round was
collected. The composite score is unchanged; this is a second score reported beside it. Since 26 November 2026 (owner's
decision, taken after round 2c) it is also averaged with the composite, at equal weight, into a summary score: see
pipeline/summary_score.py. Neither the composite nor this score is changed by that.

DEFINITION
  Pool. Every item of the round: all authored pairs and all controls. Items carry neutral codes; authors are not named.
  Predictors. Every author of the round, each in a fresh context, each predicting every item. Predictions are collected
  after all pairs are written and BEFORE any judging of the round starts. Predictors see the texts, the judgment
  questions, a description of the readers and of the measure, and nothing about any result of the round.
  Target. The round's measured gap per item: the mean over judge groups of (mean rating of version A minus mean rating
  of version B), 1-7 scale, from all of the round's panels pooled.
  Headline score (the column reported beside the composite). The shared-pool prediction score, 0-100:
      100 * mean over items NOT authored by the predictor of max(0, 1 - |predicted - measured| / 1.5)
  i.e. the round's distance rule applied to a point prediction, on other authors' pairs and the controls. Beside it,
  in points: the mean absolute error on those items (the same ranking, easier to read), and for information the mean
  absolute error on all items and on the predictor's own pairs, the correlation with the measured gaps, and the mean
  signed error.
  Comparisons between two predictors use the items neither of them wrote, so both are scored on identical items:
  a paired sign-flip test of the per-item absolute errors (20,000 flips).
  Error bars. Judge-level resampling: whole repeats (one judge model's x and y judge in one run) resampled with
  replacement within each judge group, every gap recomputed, every score recomputed (2,000 resamples): the spread of
  each predictor's score and how often each order of predictors occurs.
  Provenance. A prediction counts only if its agent read nothing before answering except its own task file, and wrote
  nothing but its own answer file.

What it measures: how well an author predicts what readers do with pairs it did not write. That is one part of
authoring skill, not all of it: the composite still scores whether an author's own pairs show their predicted gap,
how clean and original they are, and whether readers understand them.
"""
import argparse, csv, glob, itertools, json, math, os, random, re, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import score  # noqa: E402

SCALE = 1.5
NUMBER = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}

INTRO = """You are taking part in a benchmark called "Thought-experiment authoring". Authors write pairs of short scenarios that differ in one factor, and a panel of readers judges them. Your task here is to predict, for each of {n} pairs below, how big a difference the readers' judgments show.

HOW THE READERS JUDGE
- The readers are AI language models from {k} model tiers. Each reader is asked to answer as a different described adult, with an age, a background and habits of their own (some use the ends of rating scales, some the middle), giving that person's honest judgment.
- Every reader sees only ONE version of a given pair, mixed in random order with {others} other short scenarios from different authors, and answers the judgment question on a scale from 1 to 7.
- For each pair, each version is rated {r} times by each of the {k} reader models.

WHAT TO PREDICT
For each pair, predict the measured gap: the mean rating of version A minus the mean rating of version B, on the 1-7 scale, averaged over the {k} reader models. A positive number means version A is rated higher; a negative number means version B is rated higher; 0 means no difference. Give a number with one decimal, for example 1.3, -0.6 or 0.0. Possible values run from -6.0 to 6.0; in earlier rounds of this benchmark most gaps fell between -2 and +3, and the largest was about +4.5.

Predict what the readers will actually do, not what they ought to do. Some of these pairs may be your own; predict them the same way. Work from your own knowledge; do not use any tool other than reading this file and writing your answer file.

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


def load_pairs(path):
    return {p["pair_id"]: p for p in json.load(open(path, encoding="utf-8"))["pairs"]}


def author_of(p):
    return p["author"].get("tier") if p["pair_type"] == "authored" else None


def build(a):
    pairs = load_pairs(a.vignettes)
    ids = sorted(pairs)
    rng = random.Random(a.seed)
    man = {"seed": a.seed, "tag": a.tag, "vignettes": os.path.relpath(os.path.abspath(a.vignettes), ROOT),
           "task_folder": "sp%s" % a.tag, "answer_folder": "sp%sa" % a.tag,
           "instruction": INSTRUCTION, "models": {}}
    os.makedirs(a.out, exist_ok=True)
    for m in a.models:
        order = ids[:]
        rng.shuffle(order)
        codes = {"P%02d" % (i + 1): pid for i, pid in enumerate(order)}
        parts = []
        for code, pid in codes.items():
            p = pairs[pid]
            q = p["judgment_question"]
            parts.append("PAIR %s\nVersion A:\n%s\n\nVersion B:\n%s\n\nJudgment question (1 = %s; 7 = %s): %s" % (
                code, p["versions"]["A"]["text"], p["versions"]["B"]["text"], q["label_min"], q["label_max"], q["text"]))
        intro = INTRO.format(n=len(codes), k=NUMBER.get(a.judge_models, str(a.judge_models)), others=a.batch_size - 1, r=a.ratings)
        open(os.path.join(a.out, m + ".txt"), "w", encoding="utf-8").write(intro + "\n" + "\n\n==========\n\n".join(parts) + "\n" + CLOSING)
        man["models"][m] = codes
    json.dump(man, open(a.manifest, "w"), indent=1)
    print("wrote %d task files of %d items to %s; manifest %s" % (len(a.models), len(ids), a.out, a.manifest))
    print("agent folders must be named /%s/ (task) and /%s/ (answers) for the provenance check" % (man["task_folder"], man["answer_folder"]))


def check(a):
    out = {}
    tf, af = "sp%s" % a.tag, "sp%sa" % a.tag
    for f in glob.glob(os.path.join(a.transcripts, "agent-*.jsonl")):
        L = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        first = next((l for l in L if l.get("type") == "user"), None)
        if not first:
            continue
        c = first["message"]["content"]
        t = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
        mm = re.search(r"/%s/(\w+)\.txt.*?/%s/(\w+)\.json" % (tf, af), t, re.S)
        if not mm:
            continue
        m = mm.group(1)
        served, calls = set(), []
        for l in L:
            msg = l.get("message", {})
            if isinstance(msg, dict):
                if msg.get("model"):
                    served.add(msg["model"])
                for x in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
                    if isinstance(x, dict) and x.get("type") == "tool_use" and x["name"] not in ("SubagentHandback", "StructuredOutput"):
                        calls.append([x["name"], os.path.basename((x.get("input") or {}).get("file_path", "") or "")])
        w = next((i for i, cl in enumerate(calls) if cl[0] == "Write"), None)
        before, after = (calls[:w], calls[w + 1:]) if w is not None else (calls, [])
        out["pool:" + m] = {"served": sorted(served), "calls": calls,
                            "usable": w is not None and calls[w][1] == m + ".json" and len(before) >= 1
                                      and all(cl[0] == "Read" and cl[1] == m + ".txt" for cl in before)
                                      and all(cl[1] == m + ".json" for cl in after if cl[0] in ("Write", "Edit"))}
    json.dump(out, open(a.out, "w"), indent=1)
    for k in sorted(out):
        print("%-14s served %-22s usable %-5s calls %s" % (k, ",".join(out[k]["served"]), out[k]["usable"], [c[0] for c in out[k]["calls"]]))


def gaps(units, keys):
    acc = {}
    for u in keys:
        for pid, vs in units[u].items():
            for v, xs in vs.items():
                acc.setdefault(pid, {}).setdefault(u[1], {"A": [], "B": []})[v].extend(xs)
    return {pid: statistics.mean(statistics.mean(c["A"]) - statistics.mean(c["B"]) for c in per.values()) for pid, per in acc.items()}


def score_cmd(a):
    pairs = load_pairs(a.vignettes)
    man = json.load(open(a.manifest))
    prov = json.load(open(a.provenance))
    rows = score.load_judgments(os.path.join(ROOT, "judgments.csv"), a.runs)
    units = {}
    for r in rows:
        if r["pair_id"] in pairs:
            units.setdefault((r["run_id"], r["judge_group"], r["repeat"]), {}).setdefault(r["pair_id"], {}).setdefault(r["version"], []).append(r["rating"])
    gap = gaps(units, list(units))
    assert set(gap) == set(pairs), "some items have no judgments in %s" % a.runs
    preds = {}
    for m, codes in man["models"].items():
        key = next((k for k in prov if k.endswith(":" + m)), None)
        if not key or not prov[key].get("usable"):
            print("skipping %s: no usable predictions" % m)
            continue
        ans = json.load(open(os.path.join(a.answers, m + ".json")))["predictions"]
        assert sorted(x["pair"] for x in ans) == sorted(codes), m
        preds[m] = {codes[x["pair"]]: float(x["gap"]) for x in ans}
    models = sorted(preds)
    items = sorted(pairs)
    others = {m: [p for p in items if author_of(pairs[p]) != m] for m in models}
    own = {m: [p for p in items if author_of(pairs[p]) == m] for m in models}

    def pts(m, ids, g):
        return 100 * statistics.mean(max(0.0, 1 - abs(preds[m][p] - g[p]) / SCALE) for p in ids)

    def mae(m, ids, g):
        return statistics.mean(abs(preds[m][p] - g[p]) for p in ids) if ids else None

    res = {"definition": "pipeline/shared_pool.py docstring", "runs": a.runs, "manifest": a.manifest, "n_items": len(items), "predictors": {}}
    for m in models:
        xs, ys = [preds[m][p] for p in items], [gap[p] for p in items]
        res["predictors"][m] = {
            "shared_pool_score": round(pts(m, others[m], gap), 1),
            "mae_others": round(mae(m, others[m], gap), 3), "n_others": len(others[m]),
            "mae_all": round(mae(m, items, gap), 3),
            "mae_own": None if not own[m] else round(mae(m, own[m], gap), 3), "n_own": len(own[m]),
            "correlation_all": round(statistics.correlation(xs, ys), 3),
            "mean_signed_error_all": round(statistics.mean(x - y for x, y in zip(xs, ys)), 3)}
    rng = random.Random(a.seed)
    groups = sorted({u[1] for u in units})
    sims = []
    for _ in range(a.n_boot):
        keys = []
        for g in groups:
            pool = [u for u in units if u[1] == g]
            keys += rng.choices(pool, k=len(pool))
        g2 = gaps(units, keys)
        sims.append({m: pts(m, others[m], g2) for m in models})
    orders = {}
    for s in sims:
        k = " > ".join(sorted(models, key=lambda m: -s[m]))
        orders[k] = orders.get(k, 0) + 1
    res["judge_level_resampling"] = {"n": len(sims), "score_sd": {m: round(statistics.pstdev(s[m] for s in sims), 2) for m in models},
                                     "order_by_shared_pool_score": {k: round(v / len(sims), 3) for k, v in sorted(orders.items(), key=lambda kv: -kv[1])}}
    paired = {}
    for x, y in itertools.combinations(models, 2):
        ids = [p for p in items if author_of(pairs[p]) not in (x, y)]
        d = [abs(preds[x][p] - gap[p]) - abs(preds[y][p] - gap[p]) for p in ids]
        obs = statistics.mean(d)
        h = sum(1 for _ in range(a.n_perm) if abs(statistics.mean(v if rng.random() < 0.5 else -v for v in d)) >= abs(obs) - 1e-12)
        paired["%s vs %s" % (x, y)] = {"items_written_by_neither": len(ids), "mae_difference": round(obs, 3),
                                       "sign_flip_p": round((h + 1) / (a.n_perm + 1), 4)}
    res["paired_comparisons"] = paired
    json.dump(res, open(a.out, "w"), indent=1)
    for m in models:
        x = res["predictors"][m]
        print("%-7s shared-pool score %5.1f (sd %.1f)  MAE others %.2f (n %d)  all %.2f  own %s  r %.2f  signed %+.2f" % (
            m, x["shared_pool_score"], res["judge_level_resampling"]["score_sd"][m], x["mae_others"], x["n_others"], x["mae_all"],
            "-" if x["mae_own"] is None else "%.2f" % x["mae_own"], x["correlation_all"], x["mean_signed_error_all"]))
    print("order:", json.dumps(res["judge_level_resampling"]["order_by_shared_pool_score"]))
    print("paired:", json.dumps(paired))
    print("wrote", a.out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["build", "check", "score"])
    ap.add_argument("--vignettes")
    ap.add_argument("--models", nargs="*")
    ap.add_argument("--tag", default="")
    ap.add_argument("--out")
    ap.add_argument("--manifest")
    ap.add_argument("--transcripts")
    ap.add_argument("--runs")
    ap.add_argument("--answers")
    ap.add_argument("--provenance")
    ap.add_argument("--judge-models", type=int, default=4, help="build: number of judge models, for the task text")
    ap.add_argument("--batch-size", type=int, default=46, help="build: items each judge sees, for the task text")
    ap.add_argument("--ratings", type=int, default=10, help="build: ratings per model and version, for the task text")
    ap.add_argument("--seed", type=int, default=20261125)
    ap.add_argument("--n-boot", type=int, default=2000)
    ap.add_argument("--n-perm", type=int, default=20000)
    a = ap.parse_args()
    {"build": build, "check": check, "score": score_cmd}[a.step](a)
