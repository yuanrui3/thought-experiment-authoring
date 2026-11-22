#!/usr/bin/env python3
"""Build the "predict the people" task: author models predict results that real people produced.

    python3 pipeline/predict_humans/build.py --moral-evals DIR --moca DIR --out DIR [--runs 2]

Items (public data with per-item human results; texts stay out of this repository):
  OffTheRails Exp. 2: 10 scenarios x 8 versions (harm as a means or a side effect; avoidable or not;
    the agent acts or lets a colleague act). In each scenario the "means" and "side effect" versions are
    different stories (about 30% word overlap); the other two features are near-minimal edits. About 23 people rated each version on two statements, 1-5.
    The task asks for the mean rating of each statement for each version. Factor effects, the same
    60 contrasts as the panel calibration, are derived from these predictions.
  MoCa: the 89 stories that form the 85 near-minimal pairs, grouped with their look-alikes. 25 people
    answered each story's yes/no question. The task asks for the share answering yes.

One file per dataset and run; runs differ only in the order of scenarios, versions, groups and stories.
The manifest maps every item number back to its source id and holds no story text.
"""
import argparse, glob, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--moral-evals", required=True)
ap.add_argument("--moca", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--runs", type=int, default=2)
ap.add_argument("--seed", type=int, default=20261123)
ap.add_argument("--calibration-manifest", default=os.path.join(os.path.dirname(HERE), "calibration", "manifest.json"))
ap.add_argument("--manifest", default=os.path.join(HERE, "manifest.json"))
args = ap.parse_args()

otr = {}
for f in sorted(glob.glob(os.path.join(args.moral_evals, "offtherails", "prolific-exp-2", "batch_*.json"))):
    for x in json.load(open(f, encoding="utf-8")):
        otr[(x["scenario_id"], x["condition"])] = x
scen = sorted({s for s, _ in otr})
conds = sorted({c for _, c in otr})
assert len(scen) == 10 and len(conds) == 8
stories = {}
for tag, name in (("c", "causal_dataset_v1.json"), ("m", "moral_dataset_v1.json")):
    for i, s in enumerate(json.load(open(os.path.join(args.moca, "data", name), encoding="utf-8"))):
        stories["%s%03d" % (tag, i)] = json.loads(s)
comps = json.load(open(args.calibration_manifest))["moca_components"]

LABEL = {"cc": "the harm is the means to the goal", "coc": "the harm is a side effect",
         "evitable": "the harm would not happen if the agent acted differently", "inevitable": "the harm would happen anyway",
         "action_yes": "the agent does it", "prevention_no": "the agent does not stop a colleague doing it"}


def parts(c):
    a, b, rest = c.split("_", 2)
    return a, b, rest


OTR_INTRO = """This file describes {n} scenarios from a real study with ordinary adults recruited online. Your task is to predict what those people actually answered.

Each scenario was written in 8 versions, named by three features above each version: whether the harm is the means to the goal or a side effect; whether the harm would happen anyway; and whether the agent does the act or does not stop a colleague doing it. The last two features change only a sentence or two. The "means" and "side effect" versions of a scenario are different stories with the same character: the plan, the benefit and the harm all differ between them.

Each participant read 16 stories, sometimes two different versions of the same scenario. After each story they said how much they agreed with two statements, from 1 = Strongly disagree to 5 = Strongly agree (2 = Disagree, 3 = Neutral, 4 = Agree). About 23 people rated each version.

For every version, predict the average rating people gave to each statement, as a number from 1.0 to 5.0 with one decimal. Predict what these people actually answered, not what a careful philosopher would say. Differences between versions matter most: if you think a change made no difference to people, give the versions the same number.

Do not open any other file, do not search, and do not look anything up.

When you have predicted every version of every scenario, write your predictions with the Write tool to the output file named in your instructions, as JSON in exactly this form:
{{"scenarios": [{{"scenario": <scenario number>, "versions": [{{"version": <version number>, "statement1": <1.0-5.0>, "statement2": <1.0-5.0>}}, ... all 8 versions]}}, ... all {n} scenarios]}}
"""

MOCA_INTRO = """This file has {n} short stories from a real study with ordinary adults recruited online, in {g} groups of closely related stories. Each story is followed by a yes/no question. Twenty-five people answered each story's question, each person seeing the story on its own. Your task is to predict what those people actually answered.

For every story, predict the percentage of people who answered Yes, as a whole number from 0 to 100. Predict what these people actually answered, not what you think the right answer is. Stories in a group differ in small ways; if you think a difference did not change people's answers, give the stories the same number.

Do not open any other file, do not search, and do not look anything up.

When you have predicted every story, write your predictions with the Write tool to the output file named in your instructions, as JSON in exactly this form, one entry per story, using the story labels shown (such as "3.2"):
{{"stories": [{{"story": "<label>", "yes_percent": <0-100>}}, ...]}}
"""

os.makedirs(args.out, exist_ok=True)
rng = random.Random(args.seed)
man = {"seed": args.seed, "runs": {}}
for run in range(1, args.runs + 1):
    # OffTheRails
    order = scen[:]
    rng.shuffle(order)
    txt = [OTR_INTRO.format(n=len(order))]
    m_otr = {}
    for i, s in enumerate(order, 1):
        vs = conds[:]
        rng.shuffle(vs)
        x0 = otr[(s, vs[0])]
        txt.append("\n==========\nSCENARIO %d\n\nStatement 1: %s\nStatement 2: %s\n" % (i, x0["permissibility_question"], x0["intention_question"]))
        m_otr[str(i)] = {"scenario_id": s, "versions": {}}
        for j, c in enumerate(vs, 1):
            x = otr[(s, c)]
            assert x["permissibility_question"] == x0["permissibility_question"] and x["intention_question"] == x0["intention_question"]
            a, b, r = parts(c)
            txt.append("\n----------\nScenario %d, version %d (%s; %s; %s)\n\n%s %s\n\n%s\n\n%s\n\n%s\n" % (
                i, j, LABEL[a], LABEL[b], LABEL[r], x["context"], x["opportunity"], x["structure_sentence"], x["evitability_sentence"], x["action_sentence"]))
            m_otr[str(i)]["versions"][str(j)] = c
    open(os.path.join(args.out, "otr_r%d.txt" % run), "w", encoding="utf-8").write("".join(txt))
    # MoCa
    corder = [c[:] for c in comps]
    rng.shuffle(corder)
    n = sum(len(c) for c in corder)
    txt = [MOCA_INTRO.format(n=n, g=len(corder))]
    m_moca = {}
    for g, comp in enumerate(corder, 1):
        rng.shuffle(comp)
        txt.append("\n==========\nGROUP %d\n" % g)
        for k, sid in enumerate(comp, 1):
            lab = "%d.%d" % (g, k)
            txt.append("\n----------\nStory %s\n\n%s\n\nQuestion: %s\n" % (lab, stories[sid]["story"], stories[sid]["question"]))
            m_moca[lab] = sid
    open(os.path.join(args.out, "moca_r%d.txt" % run), "w", encoding="utf-8").write("".join(txt))
    man["runs"][str(run)] = {"otr": m_otr, "moca": m_moca}
json.dump(man, open(args.manifest, "w"), indent=1)
for f in sorted(os.listdir(args.out)):
    t = open(os.path.join(args.out, f), encoding="utf-8").read()
    print("%s: %d words, %d lines" % (f, len(t.split()), t.count("\n")))
