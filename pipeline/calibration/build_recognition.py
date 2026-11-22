#!/usr/bin/env python3
"""Build the recognition check: one file listing every calibration story once, asking whether the
reader recognises it from a published source. Run one judge per model on it (same rules as the
judging batches: read this file, write the answers, nothing else).

    python3 pipeline/calibration/build_recognition.py --moral-evals DIR --moca DIR --out FILE --key FILE

Stories: every MoCa story that appears in a near-minimal pair (from manifest.json), and one version
of each OffTheRails scenario (condition cc_evitable_action_yes), shuffled with a fixed seed.
The key file maps item numbers to [dataset, id]; it holds no story text.
"""
import argparse, glob, json, os, random

ap = argparse.ArgumentParser()
ap.add_argument("--moral-evals", required=True)
ap.add_argument("--moca", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--key", required=True)
ap.add_argument("--manifest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json"))
ap.add_argument("--seed", type=int, default=5)
args = ap.parse_args()
m = json.load(open(args.manifest))
otr = {}
for f in sorted(glob.glob(os.path.join(args.moral_evals, "offtherails", "prolific-exp-2", "batch_*.json"))):
    for x in json.load(open(f, encoding="utf-8")):
        otr[(x["scenario_id"], x["condition"])] = x
stories = {}
for tag, name in (("c", "causal_dataset_v1.json"), ("m", "moral_dataset_v1.json")):
    for i, s in enumerate(json.load(open(os.path.join(args.moca, "data", name), encoding="utf-8"))):
        stories["%s%03d" % (tag, i)] = json.loads(s)
items = [("moca", sid, stories[sid]["story"]) for c in m["moca_components"] for sid in c]
for s in sorted({k[0] for k in otr}):
    x = otr[(s, "cc_evitable_action_yes")]
    items.append(("otr", s, "%s %s %s %s %s" % (x["context"], x["opportunity"], x["structure_sentence"], x["evitability_sentence"], x["action_sentence"])))
random.Random(args.seed).shuffle(items)
txt = ["""This file lists %d short stories. For each one, say whether you recognise it, or a story with the same structure and setting, from a specific published source: a psychology or philosophy paper, a textbook, a well-known thought experiment, or a public dataset.

Be careful and honest: answer "yes" only if you can name the source or the classic case it comes from. A story that merely resembles a general type (for example "a moral dilemma") is "no".

Do not open any other file, do not search, and do not look anything up.

When you have gone through all of them, write your answers with the Write tool to the output file named in your instructions, as JSON in exactly this form, one entry per story, in order:
{"answers": [{"item": 1, "recognised": "yes" or "no", "source": "name of the source or classic case, or empty"}, ...]}
""" % len(items)]
for i, (_, _, t) in enumerate(items, 1):
    txt.append("\n----------\nSTORY %d\n\n%s\n" % (i, t))
os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
open(args.out, "w", encoding="utf-8").write("".join(txt))
json.dump([[d, k] for d, k, _ in items], open(args.key, "w"))
print("recognition file: %d stories, %d words" % (len(items), len("".join(txt).split())))
