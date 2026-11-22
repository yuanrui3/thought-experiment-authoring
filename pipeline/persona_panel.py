#!/usr/bin/env python3
"""Rescore the pilot with persona judges: the same batches as the Claude panel, each judge answering
as a described participant.

    python3 pipeline/persona_panel.py build  --out DIR [--models haiku sonnet opus fable]
    python3 pipeline/persona_panel.py check  --transcripts DIR --answers DIR
    python3 pipeline/persona_panel.py ingest --answers DIR

build   For each batch of the pilot's manifest (pipeline/batches.json, the same item lists and versions the
        original judges saw), writes DIR/<batch>.txt: the original judge prompt word for word (rendered by
        pipeline/api_panel.py's copy of it), plus one closing paragraph saying the "structured answer" is a
        JSON file. Draws one persona per batch (pipeline/calibration/personas.py, its own seed) and writes
        pipeline/batches_persona.json with each batch's persona and the exact instruction each judge got.
check   Reads the judges' transcripts: served model, and that each read its own batch file, then wrote its own
        answers, and wrote nothing afterwards. Any later calls are listed; they cannot change answers already written.
ingest  Rebuilds run "persona" in judgments.csv from the answer files (idempotent); every other run is kept.
"""
import argparse, csv, glob, json, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("step", choices=["build", "check", "ingest"])
ap.add_argument("--out")
ap.add_argument("--answers")
ap.add_argument("--transcripts")
ap.add_argument("--models", nargs="*", default=["haiku", "sonnet", "opus", "fable"])
ap.add_argument("--seed", type=int, default=20261125)
ap.add_argument("--run-id", default="persona")
ap.add_argument("--collected-on", default=time.strftime("%Y-%m-%d", time.gmtime()))
args = ap.parse_args()
MAN = os.path.join(HERE, "batches_persona.json")
MODEL_ID = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5", "fable": "claude-fable-5-2"}

CLOSING = ('\n\nThe "structured answer" is a JSON object of the form {"answers": [{"item": <scenario number>, "rating": '
           '<whole number 1-7>, "check": "a", "b" or "c"}, ...]}, one entry per scenario. Write it with the Write tool to '
           'the output file named in your instructions.\n')
INSTRUCTION = ("You are taking part in a study of how people judge everyday situations, as the participant described here. {persona} "
               "Answer every question as this person honestly would: people differ, and there are no right or wrong answers. "
               "Read the file {batch_file} with the Read tool and follow its instructions. Read only that one file: do not open "
               "any other file, list folders, run commands, search, or look anything up, and do not use any other tool. When you "
               "have answered every scenario, write your answers with the Write tool to {answer_file} in exactly the JSON form the "
               "file specifies. Then end your turn with the plain-text reply: done (this needs no tool).")

if args.step == "build":
    sys.path.insert(0, HERE)
    sys.argv = [sys.argv[0], "build"]  # api_panel parses its own arguments on import
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_panel_prompt", os.path.join(HERE, "api_panel.py"))
    src = open(os.path.join(HERE, "api_panel.py"), encoding="utf-8").read().split("# ---- build:")[0]
    ns = {"__file__": os.path.join(HERE, "api_panel.py"), "__name__": "api_panel_prompt"}
    exec(compile(src, "api_panel.py", "exec"), ns)
    judge_prompt = ns["judge_prompt"]
    batches = [b for b in json.load(open(os.path.join(HERE, "batches.json")))["batches"] if b["model_alias"] in args.models]
    tmp = os.path.join(args.out, "_personas.json")
    os.makedirs(args.out, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(HERE, "calibration", "personas.py"), "--n", str(len(batches)), "--seed", str(args.seed),
                    "--out", tmp], check=True, stdout=subprocess.DEVNULL)
    people = json.load(open(tmp))["personas"]
    os.remove(tmp)
    ans_dir = args.answers or os.path.join(os.path.dirname(os.path.abspath(args.out)), "pja")
    man = {"run_id": args.run_id, "persona_seed": args.seed, "source_manifest": "pipeline/batches.json", "batches": {}}
    for i, b in enumerate(batches, 1):
        items = [(it["pair_id"], it["version"]) for it in b["items"]]
        f = os.path.join(args.out, b["batch_id"] + ".txt")
        open(f, "w", encoding="utf-8").write(judge_prompt(items) + CLOSING)
        persona = people["b%02d" % i]["text"]
        man["batches"][b["batch_id"]] = {"model_alias": b["model_alias"], "repeat": b["repeat"], "arm": b["arm"], "persona": persona,
                                         "instruction": INSTRUCTION.format(persona=persona, batch_file="<batch file>", answer_file="<answer file>")}
    json.dump(man, open(MAN, "w"), indent=1)
    print("wrote %d batch files to %s and %s" % (len(batches), args.out, MAN))
    sys.exit(0)

man = json.load(open(MAN))
pilot = {b["batch_id"]: b for b in json.load(open(os.path.join(HERE, "batches.json")))["batches"]}

if args.step == "check":
    rep = {}
    for f in glob.glob(os.path.join(args.transcripts, "agent-*.jsonl")):
        L = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        first = next((l for l in L if l.get("type") == "user"), None)
        if not first:
            continue
        c = first["message"]["content"]
        t = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
        m = re.search(r"/pj/([a-z]+-r\d-[xy])\.txt", t)
        if not m or "/pja/%s.json" % m.group(1) not in t:
            continue
        bid = m.group(1)
        models, calls = set(), []
        for l in L:
            msg = l.get("message", {})
            if isinstance(msg, dict):
                if msg.get("model"):
                    models.add(msg["model"])
                for x in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
                    if isinstance(x, dict) and x.get("type") == "tool_use" and x["name"] not in ("SubagentHandback", "StructuredOutput"):
                        calls.append([x["name"], os.path.basename((x.get("input") or {}).get("file_path", "") or "")])
        ok2 = len(calls) >= 2 and calls[0] == ["Read", bid + ".txt"] and calls[1] == ["Write", bid + ".json"]
        stray = calls[2:] if ok2 else []
        rep[bid] = {"requested": MODEL_ID[man["batches"][bid]["model_alias"]], "served": sorted(models), "calls": calls,
                    "strictly_clean": ok2 and not stray,
                    # answers are final once written: a judge is usable if it read its own file, wrote its own answers,
                    # and never wrote or edited anything afterwards (later calls are listed, but cannot change the answers)
                    "usable": ok2 and not any(n in ("Write", "Edit", "NotebookEdit") for n, _ in stray),
                    "stray_calls_after_answering": stray}
    bad = [b for b, r in rep.items() if not r["usable"] or r["served"] != [r["requested"]]]
    print("%d transcripts; %d strictly clean; %d usable; served as requested: %d" % (
        len(rep), sum(r["strictly_clean"] for r in rep.values()), sum(r["usable"] for r in rep.values()),
        sum(r["served"] == [r["requested"]] for r in rep.values())))
    for b in sorted(rep):
        if rep[b]["stray_calls_after_answering"] or b in bad:
            print("  %s served %s usable %s stray %s" % (b, rep[b]["served"], rep[b]["usable"], [n for n, _ in rep[b]["stray_calls_after_answering"]]))
    json.dump(rep, open(os.path.join(HERE, "raw", "panel_persona_provenance.json"), "w"), indent=1)
    sys.exit(0)

if args.step == "ingest":
    prov_path = os.path.join(HERE, "raw", "panel_persona_provenance.json")
    prov = json.load(open(prov_path)) if os.path.exists(prov_path) else {}
    path = os.path.join(ROOT, "judgments.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        keep = [r for r in rd if r["run_id"] != args.run_id]
    new, missing, refused = [], [], []
    for bid, info in sorted(man["batches"].items()):
        f = os.path.join(args.answers, bid + ".json")
        if not os.path.exists(f):
            missing.append(bid)
            continue
        if prov and not prov.get(bid, {}).get("usable"):
            refused.append(bid)
            continue
        ans = {int(x["item"]): x for x in json.load(open(f))["answers"]}
        b = pilot[bid]
        model = MODEL_ID[info["model_alias"]]
        assert sorted(ans) == list(range(1, len(b["items"]) + 1)), bid
        for it in b["items"]:
            x = ans[it["position"]]
            assert 1 <= int(x["rating"]) <= 7 and str(x["check"]).lower() in ("a", "b", "c"), bid
            new.append({"run_id": args.run_id, "wave": args.run_id, "judge_id": "anthropic/%s/persona-%s" % (model, bid), "judge_type": "llm",
                        "judge_vendor": "anthropic", "judge_model": model, "judge_group": "anthropic/" + model, "batch_id": bid,
                        "repeat": b["repeat"], "arm": b["arm"], "position": it["position"], "batch_size": len(b["items"]),
                        "pair_id": it["pair_id"], "version": it["version"], "rating": int(x["rating"]),
                        "comprehension_answer": str(x["check"]).strip().lower(), "effort": "default", "protocol": "panel-v1-persona",
                        "collected_on": args.collected_on})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(keep + new)
    print("judgments.csv: %d rows kept from other runs, %d rows for run %r%s%s" % (
        len(keep), len(new), args.run_id, ("; no answers yet: " + " ".join(missing)) if missing else "",
        ("; refused (provenance): " + " ".join(refused)) if refused else ""))
