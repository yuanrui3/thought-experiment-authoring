#!/usr/bin/env python3
"""Generate the panel workflow script for a set of repeats (and optionally the audits).

The script embeds each vignette once and builds every judge's prompt from the
batch manifest, so judges receive their scenarios inline and need no file access.
Judges never see pair ids, authors, factors, predictions or version labels.
"""
import json, os, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

ap = argparse.ArgumentParser()
ap.add_argument("--repeats", nargs="+", type=int, required=True)
ap.add_argument("--audits", action="store_true")
ap.add_argument("--name", required=True)
ap.add_argument("--judge-effort", default="low")
args = ap.parse_args()

doc = json.load(open(os.path.join(ROOT, "vignettes.json")))
man = json.load(open(os.path.join(HERE, "batches.json")))
by_id = {p["pair_id"]: p for p in doc["pairs"] + doc["audit_calibration_pairs"]}
factors = {f["factor_id"]: f for f in doc["factors"]}

V = {}
for p in doc["pairs"]:
    for v in ("A", "B"):
        V["%s|%s" % (p["pair_id"], v)] = {
            "t": p["versions"][v]["text"], "q": p["judgment_question"]["text"],
            "l1": p["judgment_question"]["label_min"], "l7": p["judgment_question"]["label_max"],
            "c": p["comprehension_question"]["text"], "o": p["comprehension_question"]["options"],
        }
batches = [{"id": b["batch_id"], "model": b["model_alias"],
            "items": ["%s|%s" % (it["pair_id"], it["version"]) for it in b["items"]]}
           for b in man["batches"] if b["repeat"] in args.repeats]

audits = []
if args.audits:
    for a in man["audits"]:
        items = []
        for it in a["items"]:
            p = by_id[it["pair_id"]]
            f = factors[p["factor_id"]]
            declared = "%s. %s" % (f["name"], f["description"])
            if p["pair_type"] == "control_null":
                declared = "Incidental detail. A detail that should make no difference to the judgment. Detail changed: %s." % p.get("null_detail", "")
            items.append({
                "code": it["code"], "factor": declared, "intended": p["intended_difference"],
                "a": p["versions"]["A"]["text"], "b": p["versions"]["B"]["text"],
                "q": p["judgment_question"]["text"], "l1": p["judgment_question"]["label_min"],
                "l7": p["judgment_question"]["label_max"], "c": p["comprehension_question"]["text"],
                "o": p["comprehension_question"]["options"], "k": p["comprehension_question"]["correct"],
            })
        audits.append({"id": a["audit_id"], "model": a["model_alias"], "items": items})

phases = [{"title": "Judge", "detail": "fresh-context judges, one version of each pair per batch"}]
if audits:
    phases.append({"title": "Audit", "detail": "blind confound and originality audit of both versions"})
meta = {"name": args.name,
        "description": "Blind judging panel for vignette pairs (%d judge batches%s)" % (len(batches), ", plus %d auditors" % len(audits) if audits else ""),
        "phases": phases}

JS = r'''
const V = __V__
const BATCHES = __BATCHES__
const AUDITS = __AUDITS__
const JUDGE_EFFORT = __EFFORT__

const JUDGE_INTRO = (n) => `You are taking part in a study of how people judge everyday situations. Below are ${n} short, unrelated scenarios. Each is followed by two questions.

Q1 asks for your own judgment on a scale from 1 to 7. There are no right or wrong answers to Q1. Give your honest judgment of the scenario as it is written.
Q2 is a factual question about what the scenario says, with three options: a, b, c.

Treat every scenario independently: judge each one as if it were the only one you had read, and use only what that scenario states. Do not use any tools, do not open or search for files, and do not look anything up. Just read and answer.

Answer every scenario exactly once, in the order given, through the structured answer. For each scenario give: item (its number), rating (a whole number from 1 to 7 for Q1) and check (the letter a, b or c for Q2).`

function judgePrompt(b) {
  const parts = b.items.map((key, i) => {
    const v = V[key]
    return `SCENARIO ${i + 1}\n${v.t}\n\nQ1. ${v.q} (1 = ${v.l1}; 7 = ${v.l7})\nQ2. ${v.c}\n   a) ${v.o.a}\n   b) ${v.o.b}\n   c) ${v.o.c}`
  })
  return JUDGE_INTRO(b.items.length) + '\n\n' + parts.join('\n\n----------\n\n') + `\n\n----------\n\nNow answer all ${b.items.length} scenarios through the structured answer.`
}

const judgeSchema = (n) => ({
  type: 'object',
  properties: {
    answers: {
      type: 'array', minItems: n, maxItems: n,
      items: {
        type: 'object',
        properties: {
          item: { type: 'integer', minimum: 1, maximum: n },
          rating: { type: 'integer', minimum: 1, maximum: 7 },
          check: { type: 'string', enum: ['a', 'b', 'c'] },
        },
        required: ['item', 'rating', 'check'],
      },
    },
  },
  required: ['answers'],
})

const AUDIT_INTRO = (n) => `You are auditing vignette pairs written for a benchmark on philosophical thought experiments. Each pair has two versions, A and B, of a short scenario. The pair's author claims that the versions differ only in one declared factor. Readers will each see just one version and answer a 1-7 judgment question and a multiple-choice comprehension question.

For each of the ${n} pairs below you get: the declared factor, the author's one-sentence statement of the intended difference, both versions, the judgment question, and the comprehension question with its answer key.

Audit each pair on its own. Be strict and concrete, and do not give the benefit of the doubt. For each pair report:

1. factor_realized: does the difference between A and B really vary the declared factor? "yes", "partly" (it varies it only weakly or ambiguously, or only together with something else), or "no".
2. other_differences: every difference between A and B, other than the declared factor itself, that could move a reader's answer to the judgment question. Compare the two texts sentence by sentence. Look for differences in: the outcome or its severity; what people know, believe, want or foresee; probability or risk; effort or cost; who causes what, and how much; who is affected; information given to the reader in one version only; vivid or emotional wording; length. Wording that is strictly necessary to state the declared factor is not a confound. One short phrase per item; an empty list if there are none.
3. confound_severity: 0 = none, the versions differ only in the declared factor; 1 = minor, an incidental difference unlikely to move judgments; 2 = moderate, a difference that offers a plausible alternative explanation for a gap in ratings; 3 = severe, a second judgment-relevant factor clearly changes along with the declared one, so a gap in ratings could not be credited to the declared factor.
4. closest_known_case: the published thought experiment or experimental vignette that this pair most resembles (name it), or "none".
5. originality: 0 = a re-skin of a well-known case, the same structure and mechanism with names and setting changed; 1 = a close variant of an identifiable known case with a modest twist; 2 = a stock scenario type of the literature, not traceable to one specific case; 3 = a fresh scenario and mechanism.
6. question_problems: problems with the questions, such as a judgment question that is leading, double-barrelled, hints at the factor, merely restates the manipulated fact, or is likely to sit at the floor or ceiling of the scale in both versions; or a comprehension question that is ambiguous or cannot be answered from the text. An empty string if there are none.
7. comprehension_key_ok: true if the keyed answer is correct for both versions, false otherwise.

Do not use any tools other than the structured answer. Do not open or search for files, and do not look anything up. Audit all ${n} pairs and return them through the structured answer, using each pair's code.`

function auditPrompt(a) {
  const parts = a.items.map(it =>
    `PAIR ${it.code}\nDeclared factor: ${it.factor}\nAuthor's statement of the intended difference: ${it.intended}\n\nVersion A:\n${it.a}\n\nVersion B:\n${it.b}\n\nJudgment question (1 = ${it.l1}; 7 = ${it.l7}): ${it.q}\nComprehension question: ${it.c}\n   a) ${it.o.a}\n   b) ${it.o.b}\n   c) ${it.o.c}\n   Keyed answer: version A = ${it.k.A}, version B = ${it.k.B}`)
  return AUDIT_INTRO(a.items.length) + '\n\n' + parts.join('\n\n==========\n\n')
}

const auditSchema = (n) => ({
  type: 'object',
  properties: {
    audits: {
      type: 'array', minItems: n, maxItems: n,
      items: {
        type: 'object',
        properties: {
          pair: { type: 'string' },
          factor_realized: { type: 'string', enum: ['yes', 'partly', 'no'] },
          other_differences: { type: 'array', items: { type: 'string' } },
          confound_severity: { type: 'integer', minimum: 0, maximum: 3 },
          closest_known_case: { type: 'string' },
          originality: { type: 'integer', minimum: 0, maximum: 3 },
          question_problems: { type: 'string' },
          comprehension_key_ok: { type: 'boolean' },
        },
        required: ['pair', 'factor_realized', 'other_differences', 'confound_severity', 'closest_known_case', 'originality', 'question_problems', 'comprehension_key_ok'],
      },
    },
  },
  required: ['audits'],
})

function compact(b, r) {
  if (!r || !r.answers) return { id: b.id, ok: false }
  const m = {}
  for (const a of r.answers) m[a.item] = a
  let ratings = '', checks = '', missing = 0
  for (let i = 1; i <= b.items.length; i++) {
    if (m[i]) { ratings += m[i].rating; checks += m[i].check } else { ratings += '?'; checks += '?'; missing++ }
  }
  return { id: b.id, ok: missing === 0 && r.answers.length === b.items.length, r: ratings, c: checks }
}

const thunks = []
for (const b of BATCHES) {
  thunks.push(() => agent(judgePrompt(b), { label: `judge:${b.id}`, phase: 'Judge', model: b.model, effort: JUDGE_EFFORT, schema: judgeSchema(b.items.length) })
    .then(r => compact(b, r)))
}
for (const a of AUDITS) {
  thunks.push(() => agent(auditPrompt(a), { label: `audit:${a.id}`, phase: 'Audit', model: a.model, schema: auditSchema(a.items.length) })
    .then(r => ({ id: a.id, ok: !!(r && r.audits && r.audits.length === a.items.length), n: r && r.audits ? r.audits.length : 0 })))
}
const out = await parallel(thunks)
const failed = out.map((o, i) => (o && o.ok) ? null : (i < BATCHES.length ? BATCHES[i].id : AUDITS[i - BATCHES.length].id)).filter(Boolean)
if (failed.length) log(`incomplete: ${failed.join(', ')}`)
return { results: out, failed }
'''

body = (JS.replace("__V__", json.dumps(V, ensure_ascii=False))
          .replace("__BATCHES__", json.dumps(batches))
          .replace("__AUDITS__", json.dumps(audits, ensure_ascii=False))
          .replace("__EFFORT__", json.dumps(args.judge_effort)))


def js_literal(o, ind=0):
    """meta must be a pure object literal; emit it with single-quoted strings."""
    pad = "  " * ind
    if isinstance(o, dict):
        return "{\n" + "".join("%s  %s: %s,\n" % (pad, k, js_literal(v, ind + 1)) for k, v in o.items()) + pad + "}"
    if isinstance(o, list):
        return "[" + ", ".join(js_literal(v, ind + 1) for v in o) + "]"
    return "'" + str(o).replace("\\", "\\\\").replace("'", "\\'") + "'"


script = "export const meta = " + js_literal(meta) + "\n" + body
path = os.path.join(HERE, "workflow_%s.js" % args.name)
open(path, "w").write(script)
print("wrote", path, "|", len(script), "chars |", len(batches), "judge batches |", len(audits), "audits")
