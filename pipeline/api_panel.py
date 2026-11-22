#!/usr/bin/env python3
"""Run another vendor's models as a judge group on the pilot's 30 pairs, through an
OpenAI-compatible chat endpoint (here, Google's Gemini API), and add their ratings to
judgments.csv under their own run_id.

    python3 pipeline/api_panel.py build  --aliases argon=gemini-4-argon flash=gemini-3-flash-preview
    python3 pipeline/api_panel.py run    --alias argon --price-in 4 --price-out 20 --cap 4.50
    python3 pipeline/api_panel.py ingest

Design, the same as the Claude panel (pipeline/make_batches.py): for each model and each of
5 repeats the pairs are split at random into two arms; each batch holds one version of every
pair, never both, in its own random order. The manifest is written once by "build", with its own
seed, to pipeline/batches_<run>.json.

Prompt: the Claude judges' prompt (pipeline/gen_workflow.py), word for word. Those judges
answered through a structured-output tool; here a system message says that the "structured
answer" is a JSON object, and the request asks for JSON matching the same schema.

Spending: every call is logged to the ledger with a cost estimate that counts all non-prompt
tokens at the output price; before each call the script adds a pessimistic guess for the next
call to the ledger total (all models and tasks) and stops if that would pass --cap.

The key is never read or stored here: the session's network proxy adds it to requests for the
API host. Outside such a proxy, set GEMINI_API_KEY.
"""
import argparse, csv, json, os, random, re, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("step", choices=["build", "run", "ingest"])
ap.add_argument("--run-id", default="gemini")
ap.add_argument("--vendor", default="google")
ap.add_argument("--aliases", nargs="*", help="build: alias=api_model for each model")
ap.add_argument("--alias", help="run: which model alias to run")
ap.add_argument("--repeats", type=int, default=5)
ap.add_argument("--seed", type=int, default=20261122)
ap.add_argument("--price-in", type=float)
ap.add_argument("--price-out", type=float)
ap.add_argument("--cap", type=float, default=4.50)
ap.add_argument("--ledger", default=os.path.join(HERE, "calibration", "api_ledger.jsonl"))
ap.add_argument("--first-call-guess", type=float, default=0.25)
ap.add_argument("--reasoning-effort", default="low", help="matches the Claude judges' effort setting")
ap.add_argument("--endpoint", default="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
ap.add_argument("--collected-on", default=time.strftime("%Y-%m-%d", time.gmtime()))
args = ap.parse_args()

MANIFEST = os.path.join(HERE, "batches_%s.json" % args.run_id)
RAW = os.path.join(HERE, "raw", "panel_%s" % args.run_id)
doc = json.load(open(os.path.join(ROOT, "vignettes.json"), encoding="utf-8"))
pairs = {p["pair_id"]: p for p in doc["pairs"]}
pair_ids = [p["pair_id"] for p in doc["pairs"]]

# ---- the Claude judges' prompt, copied from pipeline/gen_workflow.py
JUDGE_INTRO = """You are taking part in a study of how people judge everyday situations. Below are {n} short, unrelated scenarios. Each is followed by two questions.

Q1 asks for your own judgment on a scale from 1 to 7. There are no right or wrong answers to Q1. Give your honest judgment of the scenario as it is written.
Q2 is a factual question about what the scenario says, with three options: a, b, c.

Treat every scenario independently: judge each one as if it were the only one you had read, and use only what that scenario states. Do not use any tools, do not open or search for files, and do not look anything up. Just read and answer.

Answer every scenario exactly once, in the order given, through the structured answer. For each scenario give: item (its number), rating (a whole number from 1 to 7 for Q1) and check (the letter a, b or c for Q2)."""
SYSTEM = ('The "structured answer" in the user\'s message is a JSON object of the form '
          '{"answers": [{"item": <scenario number>, "rating": <whole number 1-7>, "check": "a", "b" or "c"}, ...]}, '
          'one entry per scenario. Reply with only that JSON object.')


def judge_prompt(items):
    parts = []
    for i, (pid, v) in enumerate(items, 1):
        p = pairs[pid]
        q, c = p["judgment_question"], p["comprehension_question"]
        parts.append("SCENARIO %d\n%s\n\nQ1. %s (1 = %s; 7 = %s)\nQ2. %s\n   a) %s\n   b) %s\n   c) %s" % (
            i, p["versions"][v]["text"], q["text"], q["label_min"], q["label_max"], c["text"],
            c["options"]["a"], c["options"]["b"], c["options"]["c"]))
    n = len(items)
    return JUDGE_INTRO.format(n=n) + "\n\n" + "\n\n----------\n\n".join(parts) + \
        "\n\n----------\n\nNow answer all %d scenarios through the structured answer." % n


def schema(n):
    return {"type": "object", "properties": {"answers": {"type": "array", "minItems": n, "maxItems": n, "items": {
        "type": "object", "properties": {"item": {"type": "integer", "minimum": 1, "maximum": n},
                                         "rating": {"type": "integer", "minimum": 1, "maximum": 7},
                                         "check": {"type": "string", "enum": ["a", "b", "c"]}},
        "required": ["item", "rating", "check"]}}}, "required": ["answers"]}


# ---- build: the batch manifest, fixed before any call
if args.step == "build":
    if os.path.exists(MANIFEST):
        raise SystemExit("%s exists; delete it to rebuild" % MANIFEST)
    rng = random.Random(args.seed)
    models = dict(a.split("=", 1) for a in args.aliases)
    batches = []
    for alias, api_model in models.items():
        for rep in range(1, args.repeats + 1):
            order = pair_ids[:]
            rng.shuffle(order)
            x_gets_a = set(order[: len(order) // 2])
            for arm in ("x", "y"):
                items = [(pid, "A" if ((pid in x_gets_a) == (arm == "x")) else "B") for pid in pair_ids]
                rng.shuffle(items)
                batches.append({"batch_id": "%s-r%d-%s" % (alias, rep, arm), "model_alias": alias, "api_model": api_model,
                                "repeat": rep, "arm": arm,
                                "items": [{"position": i + 1, "pair_id": pid, "version": v} for i, (pid, v) in enumerate(items)]})
    seen = set()
    for b in batches:
        assert len({it["pair_id"] for it in b["items"]}) == len(pair_ids)
        for it in b["items"]:
            k = (b["model_alias"], b["repeat"], it["pair_id"], it["version"])
            assert k not in seen
            seen.add(k)
    json.dump({"run_id": args.run_id, "vendor": args.vendor, "seed": args.seed, "repeats": args.repeats, "models": models,
               "batches": batches}, open(MANIFEST, "w"), indent=1)
    print("wrote %s: %d batches x %d items" % (MANIFEST, len(batches), len(pair_ids)))
    sys.exit(0)

man = json.load(open(MANIFEST))


def ledger_rows():
    return [json.loads(l) for l in open(args.ledger) if l.strip()] if os.path.exists(args.ledger) else []


def valid(a, n):
    try:
        ans = a["answers"]
        return (sorted(int(x["item"]) for x in ans) == list(range(1, n + 1)) and
                all(int(x["rating"]) in range(1, 8) and str(x["check"]).strip().lower() in ("a", "b", "c") for x in ans))
    except Exception:
        return False


def call(model, prompt, n, structured):
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            "reasoning_effort": args.reasoning_effort}
    if structured:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answers", "schema": schema(n)}}
    req = urllib.request.Request(args.endpoint, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + os.environ.get("GEMINI_API_KEY", "proxy-injected")})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.load(r), None
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:400]
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(10 * 2 ** attempt)
                continue
            return None, "HTTP %d: %s" % (e.code, msg)
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(10 * 2 ** attempt)
                continue
            return None, "network error: %s" % e


# ---- run: one call per batch, resumable
if args.step == "run":
    if args.price_in is None or args.price_out is None:
        raise SystemExit("--price-in and --price-out are required (per million tokens; pass pessimistic prices)")
    os.makedirs(RAW, exist_ok=True)
    structured = True
    for b in [b for b in man["batches"] if b["model_alias"] == args.alias]:
        out = os.path.join(RAW, b["batch_id"] + ".json")
        if os.path.exists(out):
            print("%s: done before, skipped" % b["batch_id"])
            continue
        rows = ledger_rows()
        mine = [r["cost_estimate"] for r in rows if r["model"] == b["api_model"] and r.get("cost_estimate")]
        guess = max(mine) * 1.5 if mine else args.first_call_guess
        spent = sum(r.get("cost_estimate", 0.0) for r in rows)
        if spent + guess > args.cap:
            raise SystemExit("STOP before %s: spent %.3f + next call up to %.3f would pass the cap %.2f" % (b["batch_id"], spent, guess, args.cap))
        items = [(it["pair_id"], it["version"]) for it in b["items"]]
        prompt = judge_prompt(items)
        t0 = time.time()
        r, err = call(b["api_model"], prompt, len(items), structured)
        if err and structured and err.startswith("HTTP 400"):
            print("structured output refused (%s); falling back to a plain JSON reply" % err[:120])
            structured = False
            r, err = call(b["api_model"], prompt, len(items), structured)
        if err:
            raise SystemExit("%s: %s" % (b["batch_id"], err))
        u = r.get("usage", {})
        pin, tot = u.get("prompt_tokens", 0), u.get("total_tokens", 0)
        cost = pin / 1e6 * args.price_in + max(tot - pin, 0) / 1e6 * args.price_out
        content = (r.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        try:
            a = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip()))
        except json.JSONDecodeError:
            a = None
        ok = a is not None and valid(a, len(items))
        with open(args.ledger, "a") as f:
            f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": b["api_model"],
                                "served_model": r.get("model"), "job": "pilot:" + b["batch_id"], "reasoning_effort": args.reasoning_effort,
                                "structured_output": structured, "usage": u, "price_in": args.price_in, "price_out": args.price_out,
                                "cost_estimate": round(cost, 5), "seconds": round(time.time() - t0, 1), "answers_ok": ok}) + "\n")
        if ok:
            json.dump({"batch_id": b["batch_id"], "api_model": b["api_model"], "served_model": r.get("model"),
                       "structured_output": structured, "reasoning_effort": args.reasoning_effort, "usage": u,
                       "answers": a["answers"]}, open(out, "w"), indent=1)
        else:
            open(out + ".invalid.txt", "w", encoding="utf-8").write(content)
        print("%s: %s  prompt %d  other %d  cost~%.4f  ledger total~%.3f" % (
            b["batch_id"], "ok" if ok else "INVALID", pin, tot - pin, cost, spent + cost))
    sys.exit(0)

# ---- ingest: rebuild this run's rows in judgments.csv from the raw answers (idempotent)
if args.step == "ingest":
    path = os.path.join(ROOT, "judgments.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        keep = [r for r in rd if r["run_id"] != args.run_id]
    new, missing = [], []
    for b in man["batches"]:
        f = os.path.join(RAW, b["batch_id"] + ".json")
        if not os.path.exists(f):
            missing.append(b["batch_id"])
            continue
        raw = json.load(open(f))
        by_item = {int(x["item"]): x for x in raw["answers"]}
        model = raw["served_model"] or b["api_model"]
        model = model.split("/")[-1]
        for it in b["items"]:
            x = by_item[it["position"]]
            new.append({"run_id": args.run_id, "wave": args.run_id,
                        "judge_id": "%s/%s/%s" % (args.vendor, model, b["batch_id"]), "judge_type": "llm",
                        "judge_vendor": args.vendor, "judge_model": model, "judge_group": "%s/%s" % (args.vendor, model),
                        "batch_id": b["batch_id"], "repeat": b["repeat"], "arm": b["arm"], "position": it["position"],
                        "batch_size": len(b["items"]), "pair_id": it["pair_id"], "version": it["version"],
                        "rating": int(x["rating"]), "comprehension_answer": str(x["check"]).strip().lower(),
                        "effort": raw["reasoning_effort"], "protocol": "panel-v1-api", "collected_on": args.collected_on})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(keep + new)
    print("judgments.csv: %d rows kept from other runs, %d rows for run %r%s" % (
        len(keep), len(new), args.run_id, ("; batches without answers: " + " ".join(missing)) if missing else ""))
