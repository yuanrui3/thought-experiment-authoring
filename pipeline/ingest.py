#!/usr/bin/env python3
"""Turn a finished panel run into rows of judgments.csv and audits.csv.

Reads the run's journal (one validated structured answer per agent) and the
agents' transcripts (for the model actually served and any tool use), joins
them with the batch manifest, and appends to the CSVs. Re-ingesting the same
batch replaces its rows, so the step is safe to repeat.

    python3 pipeline/ingest.py --transcripts <run transcript dir> --wave 1
"""
import argparse, csv, datetime, glob, json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

J_COLS = ["run_id", "wave", "judge_id", "judge_type", "judge_vendor", "judge_model", "judge_group", "batch_id",
          "repeat", "arm", "position", "batch_size", "pair_id", "version", "rating", "comprehension_answer",
          "effort", "protocol", "collected_on"]
A_COLS = ["run_id", "auditor_id", "auditor_type", "auditor_vendor", "auditor_model", "auditor_group", "pair_id",
          "pair_code", "factor_realized", "confound_severity", "originality", "closest_known_case",
          "other_differences", "question_problems", "comprehension_key_ok", "protocol", "collected_on"]

ap = argparse.ArgumentParser()
ap.add_argument("--transcripts", required=True, help="workflow transcript directory (holds journal.jsonl)")
ap.add_argument("--wave", required=True)
ap.add_argument("--run", default="main")
ap.add_argument("--effort", default="low")
ap.add_argument("--protocol", default="panel-v1")
ap.add_argument("--vendor", default="anthropic")
args = ap.parse_args()

man = json.load(open(os.path.join(HERE, "batches.json")))
batches = {b["batch_id"]: b for b in man["batches"]}
audits = {a["audit_id"]: a for a in man["audits"]}
today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

# ---- journal: label -> validated answer
labels, results = {}, {}
for line in open(os.path.join(args.transcripts, "journal.jsonl")):
    d = json.loads(line)
    if d.get("type") == "started":
        labels[d["agentId"]] = d["label"]
    elif d.get("type") == "result":
        results[labels[d["agentId"]]] = d.get("result")
agent_of = {v: k for k, v in labels.items()}

# ---- transcripts: served model and tool use per agent
prov = {}
for meta_path in glob.glob(os.path.join(args.transcripts, "agent-*.meta.json")):
    meta = json.load(open(meta_path))
    served, tools, usage_out = set(), [], 0
    with open(meta_path.replace(".meta.json", ".jsonl")) as f:
        for line in f:
            msg = json.loads(line).get("message", {})
            if not isinstance(msg, dict):
                continue
            if msg.get("model"):
                served.add(msg["model"])
            if isinstance(msg.get("content"), list):
                tools += [b.get("name") for b in msg["content"] if isinstance(b, dict) and b.get("type") == "tool_use"]
    prov[meta["description"]] = {"requested": meta.get("model"), "served": sorted(served), "tool_calls": tools,
                                 "other_tools": sorted({t for t in tools if t != "StructuredOutput"})}

raw_dir = os.path.join(HERE, "raw")
os.makedirs(raw_dir, exist_ok=True)
shutil.copy(os.path.join(args.transcripts, "journal.jsonl"), os.path.join(raw_dir, "panel_wave%s_journal.jsonl" % args.wave))
json.dump(prov, open(os.path.join(raw_dir, "panel_wave%s_provenance.json" % args.wave), "w"), indent=1)


def served_model(label):
    p = prov.get(label, {})
    if len(p.get("served", [])) == 1:
        return p["served"][0]
    return "+".join(p.get("served", [])) or ("alias:" + str(p.get("requested")))


def read_csv(path, cols):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


# ---- judgments
jpath = os.path.join(ROOT, "judgments.csv")
old = read_csv(jpath, J_COLS)
new, bad, tool_users, n_ok = [], [], [], 0
for label, res in sorted(results.items()):
    if not label.startswith("judge:"):
        continue
    bid = label.split(":", 1)[1]
    b = batches[bid]
    n = len(b["items"])
    ans = (res or {}).get("answers") or []
    items = sorted(a["item"] for a in ans)
    if items != list(range(1, n + 1)):
        bad.append(bid)
        continue
    if prov.get(label, {}).get("other_tools"):
        tool_users.append((bid, prov[label]["other_tools"]))
    model = served_model(label)
    by_item = {a["item"]: a for a in ans}
    for it in b["items"]:
        a = by_item[it["position"]]
        new.append({"run_id": args.run, "wave": args.wave, "judge_id": "%s/%s/%s" % (args.vendor, model, bid),
                    "judge_type": "llm", "judge_vendor": args.vendor, "judge_model": model,
                    "judge_group": "%s/%s" % (args.vendor, model), "batch_id": bid, "repeat": b["repeat"],
                    "arm": b["arm"], "position": it["position"], "batch_size": n, "pair_id": it["pair_id"],
                    "version": it["version"], "rating": a["rating"], "comprehension_answer": a["check"],
                    "effort": args.effort, "protocol": args.protocol, "collected_on": today})
    n_ok += 1
replaced = {(r["run_id"], r["batch_id"]) for r in new}
kept = [r for r in old if (r["run_id"], r["batch_id"]) not in replaced]
write_csv(jpath, J_COLS, kept + new)
print("judgments: %d batches ingested (%d rows), %d invalid %s; file now has %d rows" % (n_ok, len(new), len(bad), bad, len(kept) + len(new)))
if tool_users:
    print("  !! judges that used tools other than the answer tool:", tool_users)
else:
    print("  blindness check: no judge used any tool other than the structured answer")
print("  served models:", sorted({r["judge_model"] for r in new}))

# ---- audits
apath = os.path.join(ROOT, "audits.csv")
old = read_csv(apath, A_COLS)
new, bad = [], []
for label, res in sorted(results.items()):
    if not label.startswith("audit:"):
        continue
    aid = label.split(":", 1)[1]
    a = audits[aid]
    code_to_pair = {it["code"]: it["pair_id"] for it in a["items"]}
    got = (res or {}).get("audits") or []
    codes = sorted(x["pair"].strip().upper().replace("PAIR ", "") for x in got)
    if codes != sorted(code_to_pair):
        bad.append(aid)
        continue
    model = served_model(label)
    for x in got:
        code = x["pair"].strip().upper().replace("PAIR ", "")
        new.append({"run_id": args.run, "auditor_id": "%s/%s/%s" % (args.vendor, model, aid), "auditor_type": "llm",
                    "auditor_vendor": args.vendor, "auditor_model": model, "auditor_group": "%s/%s" % (args.vendor, model),
                    "pair_id": code_to_pair[code], "pair_code": code, "factor_realized": x["factor_realized"],
                    "confound_severity": x["confound_severity"], "originality": x["originality"],
                    "closest_known_case": " ".join(x["closest_known_case"].split()),
                    "other_differences": " || ".join(" ".join(s.split()) for s in x["other_differences"]),
                    "question_problems": " ".join(x["question_problems"].split()),
                    "comprehension_key_ok": "true" if x["comprehension_key_ok"] else "false",
                    "protocol": "audit-v1", "collected_on": today})
    if prov.get(label, {}).get("other_tools"):
        print("  !! auditor %s used tools: %s" % (aid, prov[label]["other_tools"]))
if new or bad:
    replaced = {(r["run_id"], r["auditor_id"]) for r in new}
    kept = [r for r in old if (r["run_id"], r["auditor_id"]) not in replaced]
    write_csv(apath, A_COLS, kept + new)
    print("audits: %d rows ingested from %d auditors, invalid: %s; file now has %d rows" % (
        len(new), len({r["auditor_id"] for r in new}), bad, len(kept) + len(new)))
