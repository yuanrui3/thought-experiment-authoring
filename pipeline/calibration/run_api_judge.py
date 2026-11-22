#!/usr/bin/env python3
"""Run a non-Claude model as a calibration judge through an OpenAI-compatible chat endpoint
(here, Google's Gemini API), with a hard spending cap.

    python3 pipeline/calibration/run_api_judge.py --model gemini-4-argon --batches DIR --out DIR \
        --price-in 4 --price-out 20 --cap 4.50 --ledger pipeline/calibration/api_ledger.jsonl [--only b01 b02] [--recognition FILE]

Each batch file is sent once, as the user message, with a system message in place of the Claude
judges' agent prompt (same wording, except that the model replies with the JSON instead of writing
a file). One request per judge; no judge sees another batch.

Spending: every call's token counts are logged to the ledger with a cost estimate. The cost counts
all non-prompt tokens (answer plus thinking) at the output price. Before each call the script adds
the largest cost seen so far for this model (or a pessimistic first-call guess) to the ledger total,
across all models, and stops if that would pass --cap. Prices are per million tokens; pass
pessimistic ones.

The key is never read or stored here: the session's network proxy adds it to requests for this
host. Outside such a proxy, set GEMINI_API_KEY.
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--batches", help="directory of bNN.txt judging batches")
ap.add_argument("--recognition", help="recognition file (stories.txt) to send instead of batches")
ap.add_argument("--out", required=True, help="directory for answers (bNN.json, or <model>.json for recognition)")
ap.add_argument("--only", nargs="*")
ap.add_argument("--price-in", type=float, required=True)
ap.add_argument("--price-out", type=float, required=True)
ap.add_argument("--cap", type=float, required=True)
ap.add_argument("--ledger", required=True)
ap.add_argument("--reasoning-effort", default="low")
ap.add_argument("--endpoint", default="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
ap.add_argument("--first-call-guess", type=float, default=0.25, help="assumed cost of a call before any is measured")
ap.add_argument("--temperature", type=float, help="sampling temperature (default: the API's own default)")
ap.add_argument("--personas", help="personas.json: each judge bNN answers as the persona drawn for bNN")
ap.add_argument("--condition", default="", help="label recorded in the ledger, e.g. persona or temp2")
args = ap.parse_args()

SYSTEM_JUDGE = ("You are a participant in a study of how people judge everyday situations. Read the text and follow its "
                "instructions, giving your own judgment as an ordinary reader. You have no tools and cannot write files: "
                "instead, reply with only the JSON object the text asks for, and nothing else.")
SYSTEM_RECOG = ("Read the text and follow its instructions. You have no tools and cannot write files: instead, reply "
                "with only the JSON object the text asks for, and nothing else.")


def ledger_rows():
    if not os.path.exists(args.ledger):
        return []
    return [json.loads(l) for l in open(args.ledger) if l.strip()]


def spent():
    return sum(r.get("cost_estimate", 0.0) for r in ledger_rows())


def next_call_guess():
    mine = [r["cost_estimate"] for r in ledger_rows() if r["model"] == args.model and r.get("cost_estimate")]
    return max(mine) * 1.5 if mine else args.first_call_guess


PERSONAS = json.load(open(args.personas))["personas"] if args.personas else {}
SYSTEM_PERSONA = ("You are taking part in a study of how people judge everyday situations, as the participant described here. {persona} "
                  "Answer every question as this person honestly would: people differ, and there are no right or wrong answers. "
                  "Read the text and follow its instructions. You have no tools and cannot write files: instead, reply with only "
                  "the JSON object the text asks for, and nothing else.")


def call(system, text):
    body = {"model": args.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}]}
    if args.reasoning_effort != "default":
        body["reasoning_effort"] = args.reasoning_effort
    if args.temperature is not None:
        body["temperature"] = args.temperature
    req = urllib.request.Request(args.endpoint, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + os.environ.get("GEMINI_API_KEY", "proxy-injected")})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(10 * 2 ** attempt)
                continue
            raise SystemExit("HTTP %d from the API: %s" % (e.code, msg))
        except urllib.error.URLError as e:
            if attempt < 3:
                time.sleep(10 * 2 ** attempt)
                continue
            raise SystemExit("network error: %s" % e)


def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)
        return json.loads(m.group(0)) if m else None


def valid_batch(a, text):
    n1 = len(re.findall(r"Statement 1:", text))
    n2 = len(re.findall(r"\nQuestion: ", text))
    try:
        p1, p2 = a["part1"], a["part2"]
        return (sorted(int(x["item"]) for x in p1) == list(range(1, n1 + 1)) and
                sorted(int(x["item"]) for x in p2) == list(range(1, n2 + 1)) and
                all(int(x["statement1"]) in range(1, 6) and int(x["statement2"]) in range(1, 6) for x in p1) and
                all(str(x["answer"]).strip().lower() in ("yes", "no") for x in p2))
    except Exception:
        return False


def valid_recog(a, text):
    n = len(re.findall(r"\nSTORY \d+\n", text))
    try:
        return sorted(int(x["item"]) for x in a["answers"]) == list(range(1, n + 1))
    except Exception:
        return False


jobs = []
if args.recognition:
    jobs.append(("recognition", args.recognition, os.path.join(args.out, args.model + ".json"), SYSTEM_RECOG, valid_recog))
else:
    for f in sorted(os.listdir(args.batches)):
        bid = f[:-4]
        if f.endswith(".txt") and (not args.only or bid in args.only):
            system = SYSTEM_PERSONA.format(persona=PERSONAS[bid]["text"]) if PERSONAS else SYSTEM_JUDGE
            jobs.append((bid, os.path.join(args.batches, f), os.path.join(args.out, bid + ".json"), system, valid_batch))
os.makedirs(args.out, exist_ok=True)
for job, path, out, system, check in jobs:
    if os.path.exists(out):
        print("%s: answers exist, skipped" % job)
        continue
    guess = next_call_guess()
    if spent() + guess > args.cap:
        print("STOP before %s: spent %.3f + next call up to %.3f would pass the cap %.2f" % (job, spent(), guess, args.cap))
        sys.exit(2)
    text = open(path, encoding="utf-8").read()
    t0 = time.time()
    r = call(system, text)
    u = r.get("usage", {})
    pin, tot = u.get("prompt_tokens", 0), u.get("total_tokens", 0)
    cost = pin / 1e6 * args.price_in + max(tot - pin, 0) / 1e6 * args.price_out
    content = (r.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    a = parse_json(content)
    ok = a is not None and check(a, text)
    row = {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model": args.model, "served_model": r.get("model"),
           "job": job, "condition": args.condition, "temperature": args.temperature, "reasoning_effort": args.reasoning_effort, "usage": u, "price_in": args.price_in,
           "price_out": args.price_out, "cost_estimate": round(cost, 5), "seconds": round(time.time() - t0, 1), "answers_ok": ok}
    with open(args.ledger, "a") as f:
        f.write(json.dumps(row) + "\n")
    if ok:
        json.dump(a, open(out, "w"))
    else:
        open(out + ".invalid.txt", "w", encoding="utf-8").write(content)
    print("%s: %s  prompt %d  other %d  cost~%.4f  total spent~%.3f" % (job, "ok" if ok else "INVALID", pin, tot - pin, cost, spent()))
