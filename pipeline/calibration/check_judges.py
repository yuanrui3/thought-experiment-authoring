#!/usr/bin/env python3
"""Check calibration judges: served model, tools used, files touched, and that answers are complete.

    python3 pipeline/calibration/check_judges.py --transcripts DIR --answers DIR [--out provenance.json]

Reads every subagent transcript in DIR whose first message names a batch file (jb/bNN.txt),
and reports, per batch: the model that served it, every tool call with its target path, and
whether the answer file parses with the right number of entries. A judge is strictly clean if it
read its own batch file, wrote its own answer file, and did nothing else; it is usable if it did
those two first and any later call could not have shown it anything (no reading or search tools).
"""
import argparse, glob, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument("--transcripts", required=True)
ap.add_argument("--answers", required=True)
ap.add_argument("--manifest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json"))
ap.add_argument("--out")
ap.add_argument("--writes-to", default="ja", help="only transcripts whose instructions write answers into this folder name "
                                                  "(ja = the original judges, jp = the persona judges)")
args = ap.parse_args()
man = json.load(open(args.manifest))

seen = {}
for f in glob.glob(os.path.join(args.transcripts, "agent-*.jsonl")):
    lines = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
    first = next((l for l in lines if l.get("type") == "user"), None)
    if not first:
        continue
    content = first["message"]["content"]
    text = content if isinstance(content, str) else " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    m = re.search(r"/jb/(b\d\d)\.txt", text)
    if not m or ("/%s/%s.json" % (args.writes_to, m.group(1))) not in text:
        continue
    bid = m.group(1)
    models, calls = set(), []
    for l in lines:
        msg = l.get("message", {})
        if not isinstance(msg, dict):
            continue
        if msg.get("model"):
            models.add(msg["model"])
        if isinstance(msg.get("content"), list):
            for c in msg["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") not in ("SubagentHandback", "StructuredOutput"):
                    inp = c.get("input", {})
                    calls.append((c.get("name"), inp.get("file_path") or inp.get("path") or inp.get("command") or inp.get("pattern") or ""))
    seen.setdefault(bid, []).append({"transcript": os.path.basename(f), "served": sorted(models), "calls": calls})

READING_TOOLS = {"Read", "Grep", "Glob", "Bash", "WebFetch", "WebSearch", "NotebookRead", "Agent", "Task", "ToolSearch"}
report, bad = {}, []
for bid, info in sorted(man["batches"].items()):
    runs = seen.get(bid, [])
    ans_path = os.path.join(args.answers, bid + ".json")
    ok_ans, detail = False, "missing"
    if os.path.exists(ans_path):
        try:
            a = json.load(open(ans_path))
            p1, p2 = a.get("part1", []), a.get("part2", [])
            ok_ans = (sorted(x["item"] for x in p1) == list(range(1, len(info["part1"]) + 1)) and
                      sorted(x["item"] for x in p2) == list(range(1, len(info["part2"]) + 1)) and
                      all(int(x["statement1"]) in range(1, 6) and int(x["statement2"]) in range(1, 6) for x in p1) and
                      all(str(x["answer"]).strip().lower() in ("yes", "no") for x in p2))
            detail = "ok" if ok_ans else "wrong shape"
        except Exception as e:
            detail = "unreadable: %s" % e
    calls = runs[-1]["calls"] if runs else []
    first_two_ok = (len(calls) >= 2 and [n for n, _ in calls[:2]] == ["Read", "Write"]
                    and calls[0][1].endswith("/jb/%s.txt" % bid) and calls[1][1].endswith("/%s.json" % bid))
    clean = first_two_ok and len(calls) == 2
    # A judge is still usable if its only extra calls came after it wrote its answers and could not
    # have shown it anything (no reading, searching, fetching or shell tools).
    stray = calls[2:] if first_two_ok else []
    usable = first_two_ok and not any(n in READING_TOOLS or n.startswith("mcp__") and "read" in n.lower() for n, _ in stray)
    served = runs[-1]["served"] if runs else []
    report[bid] = {"requested": info["model"], "served": served, "runs": len(runs), "clean_tool_use": clean,
                   "usable": usable, "stray_calls_after_answering": stray, "answers": detail, "calls": calls}
    if not (ok_ans and usable):
        bad.append(bid)
print("%d batches in manifest | transcripts found for %d | strictly clean (one Read, one Write) %d | usable %d" % (
    len(man["batches"]), len(seen), sum(r["clean_tool_use"] for r in report.values()), len(man["batches"]) - len(bad)))
for bid in sorted(report):
    r = report[bid]
    if r["runs"]:
        print("  %s requested %-6s served %-22s runs %d  tools clean %-5s usable %-5s answers %s%s" % (
            bid, r["requested"], ",".join(r["served"]), r["runs"], r["clean_tool_use"], r["usable"], r["answers"],
            "  stray after answering: %s" % [n for n, _ in r["stray_calls_after_answering"]] if r["stray_calls_after_answering"] else ""))
if bad:
    print("not yet usable:", " ".join(bad))
if args.out:
    json.dump(report, open(args.out, "w"), indent=1)
