#!/usr/bin/env python3
"""Check the prediction runs' transcripts: served model, and that each run only read its own task
file (one or more Read calls on it) and wrote its own predictions (one Write), and nothing else.

    python3 pipeline/predict_humans/check_agents.py --transcripts DIR [--out FILE]
"""
import argparse, glob, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument("--transcripts", required=True)
ap.add_argument("--out")
args = ap.parse_args()
rep = {}
for f in glob.glob(os.path.join(args.transcripts, "agent-*.jsonl")):
    L = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    first = next((l for l in L if l.get("type") == "user"), None)
    if not first:
        continue
    c = first["message"]["content"]
    t = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    m = re.search(r"/pr/((?:otr|moca)_r\d)\.txt.*?/pa/(\w+_(?:otr|moca)_r\d)\.json", t, re.S)
    if not m:
        continue
    task, out = m.group(1), m.group(2)
    models, calls, error = set(), [], None
    for l in L:
        msg = l.get("message", {})
        if isinstance(msg, dict):
            if msg.get("model"):
                models.add(msg["model"])
            for x in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
                if isinstance(x, dict) and x.get("type") == "tool_use" and x["name"] not in ("SubagentHandback", "StructuredOutput"):
                    calls.append([x["name"], os.path.basename((x.get("input") or {}).get("file_path", "") or "")])
        if l.get("isApiErrorMessage") or (isinstance(msg, dict) and "limit" in json.dumps(msg.get("content", ""))[:300] and l.get("type") == "assistant" and not calls):
            error = error or "api error"
    reads = [c for c in calls if c[0] == "Read"]
    writes = [c for c in calls if c[0] == "Write"]
    clean = (bool(reads) and all(c[1] == task + ".txt" for c in reads) and len(writes) == 1 and writes[0][1] == out + ".json"
             and len(reads) + len(writes) == len(calls))
    new = {"task_file": task + ".txt", "served": sorted(models), "calls": calls, "clean": clean, "wrote_answers": bool(writes)}
    # Several transcripts can target the same output (e.g. attempts that hit a usage limit and wrote nothing, then a
    # successful rerun): keep the attempt that wrote answers, and count the others.
    old = rep.get(out)
    if old is not None:
        keep, drop = (new, old) if (new["wrote_answers"] and not old["wrote_answers"]) else (old, new)
        if keep["wrote_answers"] and drop["wrote_answers"]:
            raise SystemExit("two attempts wrote %s; resolve by hand" % out)
        keep["failed_attempts_without_answers"] = old.get("failed_attempts_without_answers", 0) + 1
        new = keep
    rep[out] = new
for k in sorted(rep):
    r = rep[k]
    print("%-18s served %-22s clean %-5s calls %s" % (k, ",".join(r["served"]), r["clean"], [c[0] for c in r["calls"]]))
if args.out:
    json.dump(rep, open(args.out, "w"), indent=1)
