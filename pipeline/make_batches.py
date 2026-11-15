#!/usr/bin/env python3
"""Randomise the judging panel's batches and the auditors' reading order.

Panel design: for every judge model and every repeat, the 30 pairs are split at
random into two arms. Arm x sees version A of a random half of the pairs and
version B of the other half; arm y sees the complementary versions. So no batch
ever contains both versions of a pair, every batch holds one version of every
pair, and each (pair, version, model) cell gets exactly one rating per repeat.
Item order is shuffled independently for every batch.
"""
import json, os, random, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=20261114)
ap.add_argument("--repeats", type=int, default=5)
ap.add_argument("--models", nargs="+", default=["haiku", "sonnet", "opus", "fable"])
args = ap.parse_args()

doc = json.load(open(os.path.join(ROOT, "vignettes.json")))
pair_ids = [p["pair_id"] for p in doc["pairs"]]
rng = random.Random(args.seed)

batches = []
for model in args.models:
    for rep in range(1, args.repeats + 1):
        order = pair_ids[:]
        rng.shuffle(order)
        x_gets_a = set(order[: len(order) // 2])
        for arm in ("x", "y"):
            items = [(pid, "A" if ((pid in x_gets_a) == (arm == "x")) else "B") for pid in pair_ids]
            rng.shuffle(items)
            batches.append({
                "batch_id": "%s-r%d-%s" % (model, rep, arm),
                "model_alias": model, "repeat": rep, "arm": arm,
                "items": [{"position": i + 1, "pair_id": pid, "version": v} for i, (pid, v) in enumerate(items)],
            })

# sanity: no batch has both versions; each (pair, version, model, repeat) appears once
seen = set()
for b in batches:
    ids = [it["pair_id"] for it in b["items"]]
    assert len(ids) == len(set(ids)) == len(pair_ids)
    for it in b["items"]:
        key = (b["model_alias"], b["repeat"], it["pair_id"], it["version"])
        assert key not in seen
        seen.add(key)
assert len(seen) == len(args.models) * args.repeats * len(pair_ids) * 2

# auditors: all judged pairs plus the calibration pairs, neutral ids, own random order per auditor
audit_ids = pair_ids + [p["pair_id"] for p in doc["audit_calibration_pairs"]]
audits = []
for model in args.models:
    order = audit_ids[:]
    rng.shuffle(order)
    audits.append({"audit_id": "audit-%s" % model, "model_alias": model,
                   "items": [{"code": "P%02d" % (i + 1), "pair_id": pid} for i, pid in enumerate(order)]})

out = {"seed": args.seed, "repeats": args.repeats, "models": args.models, "batches": batches, "audits": audits}
json.dump(out, open(os.path.join(HERE, "batches.json"), "w"), indent=1)
print("batches:", len(batches), "x", len(pair_ids), "items | audits:", len(audits), "x", len(audit_ids), "pairs")
