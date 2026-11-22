#!/usr/bin/env python3
"""Round 2: three contested factors replace the three the pilot found too easy.

    python3 pipeline/round2/build.py brief    --out FILE
    python3 pipeline/round2/build.py assemble [--tiers haiku sonnet opus]
    python3 pipeline/round2/build.py judges   --out DIR [--models haiku sonnet opus] [--repeats 5]
    python3 pipeline/round2/build.py auditors --out DIR [--models haiku sonnet opus]
    python3 pipeline/round2/build.py check    --transcripts DIR
    python3 pipeline/round2/build.py ingest   --judges DIR --auditors DIR

Factors in round 2 (round2/vignettes.json):
  kept from the pilot   doing_allowing, norm_causation (the pilot's pairs and classic controls, reused unchanged)
  new                   inevitable_harm, knowledge_causation, luck_wrongness (newly authored pairs, new classic controls)
  null controls         the pilot's five, reused unchanged
Authors write the new pairs from the pilot's brief, changed only where round 2 differs: the three factors, the
readers (persona judges), and the scoring (the distance rule with its demonstration requirement). Judges are persona
judges with the pilot's design (one version of every pair per batch, five repeats, two arms per model). Auditors
use the pilot's audit prompt word for word. Judgments and audits go into judgments.csv and audits.csv as run "round2".
"""
import argparse, csv, glob, json, os, random, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.dirname(HERE)
ROOT = os.path.dirname(PIPE)
R2 = os.path.join(ROOT, "round2")
RAW = os.path.join(HERE, "raw")
sys.path.insert(0, PIPE)
import build_vignettes as BV  # noqa: E402

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("step", choices=["brief", "assemble", "judges", "auditors", "check", "ingest"])
ap.add_argument("--out")
ap.add_argument("--tiers", nargs="*", default=["haiku", "sonnet", "opus", "fable"])
ap.add_argument("--models", nargs="*", default=["haiku", "sonnet", "opus", "fable"])
ap.add_argument("--repeats", type=int, default=5)
ap.add_argument("--seed", type=int, default=20261126)
ap.add_argument("--transcripts")
ap.add_argument("--judges")
ap.add_argument("--auditors")
ap.add_argument("--run-id", default="round2")
ap.add_argument("--collected-on", default=time.strftime("%Y-%m-%d", time.gmtime()))
args = ap.parse_args()
MODEL_ID = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5", "fable": "claude-fable-5-2"}

NEW_FACTORS = [
    {"factor_id": "inevitable_harm", "name": "Avoidable vs. unavoidable harm",
     "description": "Whether a harm that follows a person's action would not have happened had they acted otherwise, or would have happened anyway; the action, what the person knows and wants, and the harm are held fixed."},
    {"factor_id": "knowledge_causation", "name": "Knowing the rule, in causal judgment",
     "description": "Whether a person who broke a rule, and whose action helped bring about an outcome, knew about the rule; the action, the rule, the outcome and others' contributions are held fixed; the judgment is how much that person caused the outcome."},
    {"factor_id": "luck_wrongness", "name": "Moral luck in wrongness",
     "description": "Whether one and the same choice, made with the same knowledge and risk, turns out harmlessly or harmfully; the judgment is how wrong the choice was, not blame or punishment."},
]
KEPT = ["doing_allowing", "norm_causation"]

BRIEF = """You are an author in a benchmark called "Thought-experiment authoring". The benchmark tests whether an author can design a philosophical thought experiment that actually works when real readers judge it.

YOUR TASK
For each of the three target factors below, write one original vignette pair: three pairs in total, one per factor.

A vignette pair consists of:
1. Version A and version B: two short scenarios of at most 150 words each (a word is any whitespace-separated token; the limit is strict). The two versions must be identical, word for word, except for the text that has to change in order to vary the one target factor. Everything else that could move a reader's judgment must be the same in both versions: the outcome and how bad or good it is, what the people involved know and want, the probabilities and effort involved, who is affected, how vivid or emotional the wording is, and the length. Any difference other than the target factor is a confound and lowers your score.
2. One judgment question, identical for both versions, answered on a scale from 1 to 7. Supply the wording and the labels for 1 and for 7. A reader who has seen only one version must be able to answer it. It must not mention the factor, the other version, or any philosophical term of art.
3. One factual comprehension question about what the scenario explicitly states, with exactly three answer options (a, b, c) and the correct option for each version. The correct option may differ between versions if the question concerns the fact you changed.
4. A prediction of the result: its direction (A_higher, B_higher, or none) and its size (none, small, or large), as defined below.

TARGET FACTORS
- inevitable_harm: Avoidable versus unavoidable harm. Whether a harm that follows a person's action would not have happened if the person had acted otherwise, or would have happened anyway because of something else. What the person does, what they know and want, and the harm itself should be the same in both versions.
- knowledge_causation: Knowing the rule, in causal judgment. Whether a person who broke a rule, and whose action helped bring about an outcome, knew about the rule or did not know about it. The action, the rule, the outcome and everyone else's contributions should be the same in both versions. For this factor the judgment question must ask how much that person caused the outcome, not how much they are to blame.
- luck_wrongness: Moral luck in judgments of wrongness. Whether one and the same choice, made with the same knowledge and the same risk, happens to turn out harmlessly or harmfully because of something outside the person's control. For this factor the judgment question must ask how wrong the person's choice was, not how much blame or punishment the person deserves.

HOW YOUR PAIRS WILL BE TESTED
- A panel of independent readers judges your scenarios. Every reader sees only one version of a given pair, in a fresh context, with no mention of the factor or of your prediction, and answers your two questions. Readers see scenarios from many authors mixed together in random order.
- In this round the readers are AI language models from several model tiers. Each reader is asked to answer as a different described adult, with an age, a background and habits of their own, giving that person's honest judgment. Human readers are planned for later rounds. Write for an ordinary adult reader with no philosophy training.
- The measured result is the mean rating for version A minus the mean rating for version B, in scale points. Size is defined on its absolute value: none = below 0.5 points; small = 0.5 or more but below 1.5; large = 1.5 or more. If you predict size "none", predict direction "none", and the other way round.

SCORING
1. Prediction: how close the measured difference comes to the range you predicted. You get full credit if it falls inside your range, and the credit falls to nothing at 1.5 points outside it. A pair whose difference is not confirmed in the direction you predicted earns nothing for prediction. A difference is confirmed when it is at least 0.5 points, its 95% interval excludes zero, and the reader models agree on its direction. So design pairs that do move readers, and predict how much; a "none" prediction cannot score.
2. Confounds: any difference between the versions other than the target factor counts against you.
3. Originality: invent your own scenarios. Re-skins of famous cases do not count: for example trolley cases, Gettier cases, Knobe's chairman, the experience machine, or any other well-known case or published experimental vignette with the names and setting changed.
4. Comprehension: the share of readers who answer your comprehension question correctly.

RULES
- Work from your own knowledge. Do not use web search, and do not use any tool other than reading this file and writing your answer file.
- Plain, concrete English. No philosophical jargon inside the scenarios or the questions.
- Be honest in your prediction: predict what you really expect the panel to do.

YOUR ANSWER
Write your three pairs with the Write tool to the output file named in your instructions, as one JSON object of exactly this form:
{"pairs": [{"factor_id": "inevitable_harm" or "knowledge_causation" or "luck_wrongness", "title": "short neutral title (not shown to readers)", "version_a": "...", "version_b": "...", "intended_difference": "one sentence: exactly what differs between A and B", "judgment_question": "...", "scale_label_1": "...", "scale_label_7": "...", "comprehension_question": "...", "option_a": "...", "option_b": "...", "option_c": "...", "correct_option_version_a": "a" or "b" or "c", "correct_option_version_b": "a" or "b" or "c", "predicted_direction": "A_higher" or "B_higher" or "none", "predicted_size": "none" or "small" or "large", "prediction_rationale": "one or two sentences: why you expect this result", "originality_note": "one sentence: how this differs from known cases"}, ... one per factor]}
"""

# the pilot's judge and audit prompts, copied from pipeline/gen_workflow.py's script (checked against it below)
JUDGE_INTRO = """You are taking part in a study of how people judge everyday situations. Below are {n} short, unrelated scenarios. Each is followed by two questions.

Q1 asks for your own judgment on a scale from 1 to 7. There are no right or wrong answers to Q1. Give your honest judgment of the scenario as it is written.
Q2 is a factual question about what the scenario says, with three options: a, b, c.

Treat every scenario independently: judge each one as if it were the only one you had read, and use only what that scenario states. Do not use any tools, do not open or search for files, and do not look anything up. Just read and answer.

Answer every scenario exactly once, in the order given, through the structured answer. For each scenario give: item (its number), rating (a whole number from 1 to 7 for Q1) and check (the letter a, b or c for Q2)."""
JUDGE_CLOSING = ('\n\nThe "structured answer" is a JSON object of the form {"answers": [{"item": <scenario number>, "rating": '
                 '<whole number 1-7>, "check": "a", "b" or "c"}, ...]}, one entry per scenario. Write it with the Write tool to '
                 'the output file named in your instructions.\n')
AUDIT_CLOSING = ('\n\nThe "structured answer" is a JSON object of the form {"audits": [{"pair": "<code>", "factor_realized": "yes", '
                 '"partly" or "no", "other_differences": ["..."], "confound_severity": 0-3, "closest_known_case": "...", '
                 '"originality": 0-3, "question_problems": "...", "comprehension_key_ok": true or false}, ...]}, one entry per pair. '
                 'Write it with the Write tool to the output file named in your instructions.\n')
PERSONA_INSTRUCTION = ("You are taking part in a study of how people judge everyday situations, as the participant described here. {persona} "
                       "Answer every question as this person honestly would: people differ, and there are no right or wrong answers. "
                       "Read the file {batch_file} with the Read tool and follow its instructions. Read only that one file: do not open "
                       "any other file, list folders, run commands, search, or look anything up, and do not use any other tool. When you "
                       "have answered every scenario, write your answers with the Write tool to {answer_file} in exactly the JSON form the "
                       "file specifies. Then end your turn with the plain-text reply: done (this needs no tool).")


def audit_intro():
    js = open(os.path.join(PIPE, "gen_workflow.py"), encoding="utf-8").read()
    m = re.search(r"const AUDIT_INTRO = \(n\) => `(.*?)`\n", js, re.S)
    return m.group(1).replace("${n}", "{n}")


def judge_prompt(pairs, items):
    parts = []
    for i, (pid, v) in enumerate(items, 1):
        p = pairs[pid]
        q, c = p["judgment_question"], p["comprehension_question"]
        parts.append("SCENARIO %d\n%s\n\nQ1. %s (1 = %s; 7 = %s)\nQ2. %s\n   a) %s\n   b) %s\n   c) %s" % (
            i, p["versions"][v]["text"], q["text"], q["label_min"], q["label_max"], c["text"], c["options"]["a"], c["options"]["b"], c["options"]["c"]))
    n = len(items)
    return JUDGE_INTRO.format(n=n) + "\n\n" + "\n\n----------\n\n".join(parts) + "\n\n----------\n\nNow answer all %d scenarios through the structured answer." % n


def load_r2():
    return json.load(open(os.path.join(R2, "vignettes.json"), encoding="utf-8"))


if args.step == "brief":
    open(args.out, "w", encoding="utf-8").write(BRIEF)
    print("wrote", args.out, len(BRIEF.split()), "words")
    sys.exit(0)

if args.step == "assemble":
    pilot = json.load(open(os.path.join(ROOT, "vignettes.json"), encoding="utf-8"))
    prov = json.load(open(os.path.join(RAW, "provenance.json"))) if os.path.exists(os.path.join(RAW, "provenance.json")) else {}
    pairs = []
    for tier in args.tiers:
        f = os.path.join(RAW, "authoring", tier + ".json")
        if not os.path.exists(f):
            print("no round-2 pairs yet from", tier)
            continue
        pv = prov.get("author:" + tier, {})
        served = (pv.get("served") or [MODEL_ID[tier]])[0]
        author = {"type": "llm", "vendor": "anthropic", "tier": tier, "model": served, "author_id": "anthropic/%s" % served,
                  "requested_alias": tier, "tool_calls": [c[0] for c in pv.get("calls", [])], "authoring_run": "round2-2026-11-22"}
        got = json.load(open(f, encoding="utf-8"))["pairs"]
        seen = set()
        for p in got:
            if p["factor_id"] not in {x["factor_id"] for x in NEW_FACTORS} or p["factor_id"] in seen:
                raise SystemExit("%s: unexpected or duplicate factor %s" % (tier, p["factor_id"]))
            seen.add(p["factor_id"])
            pairs.append(BV.shape(p, "r2_%s_%s" % (tier, p["factor_id"]), "authored", author))
        if len(seen) != 3:
            raise SystemExit("%s wrote %d of 3 factors" % (tier, len(seen)))
    builder = {"type": "researcher", "vendor": "anthropic", "author_id": "pilot-builder",
               "note": "Control pairs written by the pilot's builder, an AI system; not an evaluated author."}
    for p in json.load(open(os.path.join(HERE, "controls.json"), encoding="utf-8"))["pairs"]:
        pairs.append(BV.shape(p, p["pair_id"], p["pair_type"], builder))
    reused = [p for p in pilot["pairs"] if (p["pair_type"] in ("authored", "control_classic") and p["factor_id"] in KEPT) or p["pair_type"] == "control_null"]
    for p in reused:
        q = json.loads(json.dumps(p))
        q["reused_from"] = pilot["release"]
        pairs.append(q)
    factors = [f for f in BV.FACTORS if f["factor_id"] in KEPT] + NEW_FACTORS + [f for f in BV.FACTORS if f["factor_id"] == "null"]
    doc = {"schema_version": pilot["schema_version"], "benchmark": pilot["benchmark"], "release": "round2-2026-11-22",
           "language": "en", "task": pilot["task"], "factors": factors, "pairs": pairs, "audit_calibration_pairs": [],
           "note": "Round 2 replaces intention vs. accident, knowledge vs. lucky true belief and moral luck (every pilot author "
                   "got their direction right) with three contested factors. Pairs for doing vs. allowing and norm violation, their "
                   "classic controls and the null controls are reused from the pilot unchanged."}
    os.makedirs(R2, exist_ok=True)
    json.dump(doc, open(os.path.join(R2, "vignettes.json"), "w"), indent=1, ensure_ascii=False)
    print("wrote round2/vignettes.json:", len(pairs), "pairs")
    for p in pairs:
        flag = ("  !! " + "; ".join(p["format_problems"])) if p.get("format_problems") else ""
        print("  %-30s %-16s %-20s A=%3d B=%3d%s" % (p["pair_id"], p["pair_type"], p["factor_id"], p["versions"]["A"]["word_count"],
                                                     p["versions"]["B"]["word_count"], flag))
    sys.exit(0)

if args.step == "judges":
    doc = load_r2()
    pairs = {p["pair_id"]: p for p in doc["pairs"]}
    ids = [p["pair_id"] for p in doc["pairs"]]
    rng = random.Random(args.seed)
    batches = []
    for model in args.models:
        for rep in range(1, args.repeats + 1):
            order = ids[:]
            rng.shuffle(order)
            x_gets_a = set(order[: len(order) // 2])
            for arm in ("x", "y"):
                items = [(pid, "A" if ((pid in x_gets_a) == (arm == "x")) else "B") for pid in ids]
                rng.shuffle(items)
                batches.append({"batch_id": "r2-%s-r%d-%s" % (model, rep, arm), "model_alias": model, "repeat": rep, "arm": arm,
                                "items": [{"position": i + 1, "pair_id": pid, "version": v} for i, (pid, v) in enumerate(items)]})
    tmp = os.path.join(args.out, "_personas.json")
    os.makedirs(args.out, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(PIPE, "calibration", "personas.py"), "--n", str(len(batches)), "--seed", str(args.seed),
                    "--out", tmp], check=True, stdout=subprocess.DEVNULL)
    people = json.load(open(tmp))["personas"]
    os.remove(tmp)
    for i, b in enumerate(batches, 1):
        b["persona"] = people["b%02d" % i]["text"]
        open(os.path.join(args.out, b["batch_id"] + ".txt"), "w", encoding="utf-8").write(
            judge_prompt(pairs, [(it["pair_id"], it["version"]) for it in b["items"]]) + JUDGE_CLOSING)
    json.dump({"run_id": args.run_id, "seed": args.seed, "persona_seed": args.seed, "instruction": PERSONA_INSTRUCTION, "batches": batches},
              open(os.path.join(HERE, "judge_batches.json"), "w"), indent=1)
    print("wrote %d judge batches of %d items to %s" % (len(batches), len(ids), args.out))
    sys.exit(0)

if args.step == "auditors":
    doc = load_r2()
    new = [p for p in doc["pairs"] if p["factor_id"] in {f["factor_id"] for f in NEW_FACTORS}]
    fac = {f["factor_id"]: f for f in doc["factors"]}
    rng = random.Random(args.seed + 1)
    intro = audit_intro()
    os.makedirs(args.out, exist_ok=True)
    man = {"run_id": args.run_id, "auditors": {}}
    for model in args.models:
        order = [p["pair_id"] for p in new]
        rng.shuffle(order)
        codes = {"Q%02d" % (i + 1): pid for i, pid in enumerate(order)}
        parts = []
        for code, pid in codes.items():
            p = {q["pair_id"]: q for q in new}[pid]
            f = fac[p["factor_id"]]
            k = p["comprehension_question"]["correct"]
            parts.append("PAIR %s\nDeclared factor: %s. %s\nAuthor's statement of the intended difference: %s\n\nVersion A:\n%s\n\nVersion B:\n%s\n\n"
                         "Judgment question (1 = %s; 7 = %s): %s\nComprehension question: %s\n   a) %s\n   b) %s\n   c) %s\n   Keyed answer: version A = %s, version B = %s" % (
                             code, f["name"], f["description"], p["intended_difference"], p["versions"]["A"]["text"], p["versions"]["B"]["text"],
                             p["judgment_question"]["label_min"], p["judgment_question"]["label_max"], p["judgment_question"]["text"],
                             p["comprehension_question"]["text"], p["comprehension_question"]["options"]["a"], p["comprehension_question"]["options"]["b"],
                             p["comprehension_question"]["options"]["c"], k["A"], k["B"]))
        text = intro.format(n=len(codes)) + "\n\n" + "\n\n==========\n\n".join(parts) + AUDIT_CLOSING
        open(os.path.join(args.out, "audit-%s.txt" % model), "w", encoding="utf-8").write(text)
        man["auditors"][model] = codes
    json.dump(man, open(os.path.join(HERE, "audit_batches.json"), "w"), indent=1)
    print("wrote %d auditor files of %d pairs to %s" % (len(args.models), len(new), args.out))
    sys.exit(0)

if args.step == "check":
    out = {}
    # authors: first message names the brief and r2a/<tier>.json
    for f in glob.glob(os.path.join(args.transcripts, "agent-*.jsonl")):
        L = [json.loads(l) for l in open(f, encoding="utf-8") if l.strip()]
        first = next((l for l in L if l.get("type") == "user"), None)
        if not first:
            continue
        c = first["message"]["content"]
        t = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
        for kind, rx in (("author", r"/r2brief/brief\.txt.*?/r2a/(\w+)\.json"), ("auditor", r"/r2aud/audit-(\w+)\.txt.*?/r2aa/"),
                         ("judge", r"/r2j/(r2-\w+-r\d-[xy])\.txt.*?/r2ja/")):
            m = re.search(rx, t, re.S)
            if not m:
                continue
            models, calls = set(), []
            for l in L:
                msg = l.get("message", {})
                if isinstance(msg, dict):
                    if msg.get("model"):
                        models.add(msg["model"])
                    for x in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
                        if isinstance(x, dict) and x.get("type") == "tool_use" and x["name"] not in ("SubagentHandback", "StructuredOutput"):
                            calls.append([x["name"], os.path.basename((x.get("input") or {}).get("file_path", "") or "")])
            key = "%s:%s" % (kind, m.group(1))
            own = {"author": m.group(1) + ".json", "auditor": "audit-%s.json" % m.group(1), "judge": m.group(1) + ".json"}[kind]
            wrote_at = next((i for i, cl in enumerate(calls) if cl[0] == "Write"), None)
            before = calls[:wrote_at] if wrote_at is not None else calls
            after = calls[wrote_at + 1:] if wrote_at is not None else []
            clean_read = all(cl[0] == "Read" for cl in before) and len(before) >= 1
            # Judgment call (22 Nov): an agent may correct its own answer file after writing it (Write or
            # Edit to that same file); any write to another file, or any read before the first write
            # other than its own instructions, makes it unusable.
            later_writes = [cl for cl in after if cl[0] in ("Write", "Edit")]
            out[key] = {"served": sorted(models), "calls": calls, "wrote": wrote_at is not None,
                        "only_read_its_file_before_writing": clean_read,
                        "revised_own_answer_after_writing": bool(later_writes),
                        "usable": wrote_at is not None and calls[wrote_at][1] == own and clean_read
                                  and all(cl[1] == own for cl in later_writes),
                        "stray_calls_after_answering": after}
    json.dump(out, open(os.path.join(RAW, "provenance.json"), "w"), indent=1)
    for k in sorted(out):
        r = out[k]
        print("%-26s served %-22s usable %-5s calls %s" % (k, ",".join(r["served"]), r["usable"], [c[0] for c in r["calls"]]))
    sys.exit(0)

if args.step == "ingest":
    man = json.load(open(os.path.join(HERE, "judge_batches.json")))
    prov = json.load(open(os.path.join(RAW, "provenance.json")))
    path = os.path.join(ROOT, "judgments.csv")
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        cols = rd.fieldnames
        keep = [r for r in rd if r["run_id"] != args.run_id]
    new, missing = [], []
    for b in man["batches"]:
        f = os.path.join(args.judges, b["batch_id"] + ".json")
        pv = prov.get("judge:" + b["batch_id"], {})
        if not os.path.exists(f) or not pv.get("usable"):
            missing.append(b["batch_id"])
            continue
        ans = {int(x["item"]): x for x in json.load(open(f))["answers"]}
        assert sorted(ans) == list(range(1, len(b["items"]) + 1)), b["batch_id"]
        model = MODEL_ID[b["model_alias"]]
        for it in b["items"]:
            x = ans[it["position"]]
            new.append({"run_id": args.run_id, "wave": args.run_id, "judge_id": "anthropic/%s/%s" % (model, b["batch_id"]), "judge_type": "llm",
                        "judge_vendor": "anthropic", "judge_model": model, "judge_group": "anthropic/" + model, "batch_id": b["batch_id"],
                        "repeat": b["repeat"], "arm": b["arm"], "position": it["position"], "batch_size": len(b["items"]),
                        "pair_id": it["pair_id"], "version": it["version"], "rating": int(x["rating"]),
                        "comprehension_answer": str(x["check"]).strip().lower(), "effort": "default", "protocol": "panel-v2-persona",
                        "collected_on": args.collected_on})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(keep + new)
    print("judgments.csv: %d rows for run %r%s" % (len(new), args.run_id, ("; not ingested: " + " ".join(missing)) if missing else ""))
    am = json.load(open(os.path.join(HERE, "audit_batches.json")))
    apath = os.path.join(ROOT, "audits.csv")
    with open(apath, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        acols = rd.fieldnames
        akeep = [r for r in rd if r["run_id"] != args.run_id]
    anew = []
    for model, codes in am["auditors"].items():
        f = os.path.join(args.auditors, "audit-%s.json" % model)
        if not os.path.exists(f) or not prov.get("auditor:" + model, {}).get("usable"):
            print("auditor %s: no usable audit" % model)
            continue
        mid = MODEL_ID[model]
        for a in json.load(open(f))["audits"]:
            pid = codes[a["pair"]]
            anew.append({"run_id": args.run_id, "auditor_id": "anthropic/%s/audit-%s-r2" % (mid, model), "auditor_type": "llm",
                         "auditor_vendor": "anthropic", "auditor_model": mid, "auditor_group": "anthropic/" + mid, "pair_id": pid,
                         "pair_code": a["pair"], "factor_realized": a["factor_realized"], "confound_severity": int(a["confound_severity"]),
                         "originality": int(a["originality"]), "closest_known_case": a["closest_known_case"],
                         "other_differences": " || ".join(a["other_differences"]) if isinstance(a["other_differences"], list) else a["other_differences"],
                         "question_problems": a["question_problems"], "comprehension_key_ok": bool(a["comprehension_key_ok"]),
                         "protocol": "audit-v1-file", "collected_on": args.collected_on})
    with open(apath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=acols)
        w.writeheader()
        w.writerows(akeep + anew)
    print("audits.csv: %d rows for run %r" % (len(anew), args.run_id))
