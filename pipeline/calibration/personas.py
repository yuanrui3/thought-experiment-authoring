#!/usr/bin/env python3
"""Draw one participant persona per calibration judge, for the overconfidence test.

    python3 pipeline/calibration/personas.py [--n 40] [--seed 20261124] [--out pipeline/calibration/personas.json]

Each judge (batch bNN) answers as one described person, as a real participant answers every story as
the same person. Attributes are drawn independently with rough weights for an online US adult sample.
They include the habits that make real ratings spread out (how the person uses rating scales, how
carefully they read). Nothing in a persona mentions the stories or what the study is about.
"""
import argparse, json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=40)
ap.add_argument("--seed", type=int, default=20261124)
ap.add_argument("--out", default=os.path.join(HERE, "personas.json"))
args = ap.parse_args()
rng = random.Random(args.seed)

ATTR = {
    "age": ([("19", 1), ("23", 2), ("27", 3), ("31", 3), ("36", 3), ("42", 3), ("48", 2), ("55", 2), ("61", 1), ("68", 1)]),
    "gender": ([("woman", 48), ("man", 48), ("non-binary person", 4)]),
    "region": ([("the Northeast", 17), ("the Midwest", 21), ("the South", 38), ("the West", 24)]),
    "education": ([("a high-school diploma", 25), ("some college", 28), ("a bachelor's degree", 32), ("a graduate degree", 15)]),
    "job": ([("a nurse", 1), ("a warehouse worker", 1), ("a retail manager", 1), ("a software tester", 1), ("a high-school teacher", 1),
             ("an electrician", 1), ("an accountant", 1), ("a stay-at-home parent", 1), ("a student", 1), ("a truck driver", 1),
             ("a receptionist", 1), ("a sales representative", 1), ("a retired postal worker", 1), ("a hairdresser", 1),
             ("a line cook", 1), ("a paralegal", 1), ("a graphic designer", 1), ("between jobs", 1), ("a call-centre agent", 1),
             ("a small-business owner", 1)]),
    "politics": ([("liberal", 30), ("moderate", 30), ("conservative", 28), ("not interested in politics", 12)]),
    "religion": ([("not religious", 40), ("somewhat religious", 38), ("very religious", 22)]),
    "reading": ([("You read every story carefully.", 40), ("You read at an ordinary pace.", 40), ("You tend to read quickly and go with your first impression.", 20)]),
    "scales": ([("When you rate things you often pick the middle of the scale.", 22), ("When you rate things you often pick the ends of the scale.", 22),
                ("You tend to agree with statements more than most people.", 14), ("You tend to disagree with statements more than most people.", 14),
                ("You have no particular habit in how you use rating scales.", 28)]),
}


def draw(opts):
    vals, w = zip(*opts)
    return rng.choices(vals, weights=w, k=1)[0]


def coherent(a):
    age = int(a["age"])
    if age < 22 and a["education"] in ("a bachelor's degree", "a graduate degree"):
        return False
    if age < 25 and a["education"] == "a graduate degree":
        return False
    if a["job"] == "a student" and age > 34:
        return False
    if a["job"] == "a retired postal worker" and age < 58:
        return False
    if age < 22 and a["job"] in ("an accountant", "a paralegal", "a high-school teacher", "a nurse", "a retail manager", "a small-business owner"):
        return False
    if a["job"] in ("a high-school teacher", "an accountant") and a["education"] in ("a high-school diploma", "some college"):
        return False
    return True


def job_phrase(job):
    if job == "between jobs":
        return ", currently between jobs"
    if job == "a student":
        return ", currently a student"
    if job == "a stay-at-home parent":
        return ", a stay-at-home parent"
    if job.startswith("a retired"):
        return ", " + job
    return ", working as " + job


people = {}
for i in range(1, args.n + 1):
    a = {k: draw(v) for k, v in ATTR.items()}
    while not coherent(a):
        a = {k: draw(v) for k, v in ATTR.items()}
    pol = "You are not interested in politics." if a["politics"] == "not interested in politics" else "Politically you are %s." % a["politics"]
    text = "You are a %s-year-old %s from %s%s. Your education: %s. %s You are %s. %s %s" % (
        a["age"], a["gender"], a["region"], job_phrase(a["job"]), a["education"],
        pol, a["religion"], a["reading"], a["scales"])
    people["b%02d" % i] = {"attributes": a, "text": text}
json.dump({"seed": args.seed, "personas": people}, open(args.out, "w"), indent=1)
print("wrote %d personas to %s; e.g. %s" % (len(people), args.out, people["b01"]["text"]))
