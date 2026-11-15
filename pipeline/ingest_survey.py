#!/usr/bin/env python3
"""Turn survey completion codes into rows of judgments.csv.

    python3 pipeline/ingest_survey.py codes.txt            # one code per line; blank lines and notes are skipped
    python3 pipeline/ingest_survey.py codes.txt --run human-1

Each code is checked (format, checksum, that its items belong to its form) and
decoded with pipeline/survey_manifest.json. Rows are appended to judgments.csv
with judge_type "human"; a participant who is ingested twice replaces their
earlier rows. Also writes participants.csv (one row per participant, no
personal data: the survey collects none).
"""
import argparse, csv, datetime, json, os, re, statistics, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
J_COLS = ["run_id", "wave", "judge_id", "judge_type", "judge_vendor", "judge_model", "judge_group", "batch_id",
          "repeat", "arm", "position", "batch_size", "pair_id", "version", "rating", "comprehension_answer",
          "effort", "protocol", "collected_on"]
P_COLS = ["run_id", "participant", "form", "philosophy", "english", "familiar", "n_answered", "n_correct",
          "median_seconds", "collected_on"]
BG = {"philosophy": {"0": "", "1": "none", "2": "a course or two", "3": "a degree or more"},
      "english": {"0": "", "1": "first language", "2": "fluent", "3": "with some effort"},
      "familiar": {"0": "", "1": "no", "2": "one or two", "3": "several"}}


def check(s):
    a, b = 1, 0
    for ch in s:
        a = (a + ord(ch)) % 65521
        b = (b + a) % 65521
    n, out = b * 65536 + a, ""
    while True:
        n, r = divmod(n, 36)
        out = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + out
        if n == 0:
            return out


def decode(code, manifest):
    """Returns (participant dict, answers list) or raises ValueError with the reason."""
    code = re.sub(r"\s+", "", code)
    m = re.fullmatch(r"(TE1-([a-z2-9]{8})-(f\d\d)-([0-3]{3})-([a-z0-9]*))-([a-z0-9]+)", code)
    if not m:
        raise ValueError("not a completion code")
    body, pid, form, bg, answers, chk = m.groups()
    if check(body) != chk:
        raise ValueError("checksum does not match (the code was probably cut or altered when copied)")
    if form not in manifest["forms"]:
        raise ValueError("unknown form %s" % form)
    if len(answers) % 6:
        raise ValueError("answers have the wrong length")
    allowed = set(manifest["forms"][form])
    out, seen = [], set()
    for k in range(0, len(answers), 6):
        item, rating, opt, secs = answers[k:k + 2], answers[k + 2], answers[k + 3], answers[k + 4:k + 6]
        if item not in allowed or item in seen:
            raise ValueError("item %s does not belong to form %s or is repeated" % (item, form))
        if rating not in "1234567" or opt not in "abc":
            raise ValueError("bad answer for item %s" % item)
        seen.add(item)
        key = manifest["items"][item]
        out.append({"position": len(out) + 1, "pair_id": key["pair_id"], "version": key["version"],
                    "rating": int(rating), "comprehension_answer": opt, "seconds": int(secs, 36)})
    person = {"participant": pid, "form": form, "philosophy": BG["philosophy"][bg[0]],
              "english": BG["english"][bg[1]], "familiar": BG["familiar"][bg[2]]}
    return person, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("codes", help="text file with one completion code per line")
    ap.add_argument("--run", default="human-1")
    ap.add_argument("--group", default="human/volunteers", help="judge_group for these participants")
    ap.add_argument("--root", default=ROOT, help="project folder holding vignettes.json and judgments.csv")
    args = ap.parse_args()

    manifest = json.load(open(os.path.join(HERE, "survey_manifest.json")))
    doc = json.load(open(os.path.join(args.root, "vignettes.json"), encoding="utf-8"))
    key = {p["pair_id"]: p["comprehension_question"]["correct"] for p in doc["pairs"]}
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    rows, people, bad = [], [], []
    for n, line in enumerate(open(args.codes, encoding="utf-8"), 1):
        found = re.search(r"TE1-[A-Za-z0-9\-\s]+", line)
        if not found:
            continue
        try:
            person, answers = decode(found.group(0).strip(), manifest)
        except ValueError as e:
            bad.append((n, str(e)))
            continue
        if any(p["participant"] == person["participant"] for p in people):
            bad.append((n, "participant %s appears twice in this file; second copy skipped" % person["participant"]))
            continue
        correct = sum(1 for a in answers if a["comprehension_answer"] == key[a["pair_id"]][a["version"]])
        person.update({"run_id": args.run, "n_answered": len(answers), "n_correct": correct,
                       "median_seconds": statistics.median([a["seconds"] for a in answers]) if answers else "",
                       "collected_on": today})
        people.append(person)
        jid = "human/%s" % person["participant"]
        for a in answers:
            rows.append({"run_id": args.run, "wave": args.run, "judge_id": jid, "judge_type": "human", "judge_vendor": "",
                         "judge_model": "", "judge_group": args.group, "batch_id": person["participant"], "repeat": "",
                         "arm": person["form"], "position": a["position"], "batch_size": len(answers),
                         "pair_id": a["pair_id"], "version": a["version"], "rating": a["rating"],
                         "comprehension_answer": a["comprehension_answer"], "effort": "", "protocol": manifest["protocol"],
                         "collected_on": today})

    def merge(path, cols, new, keyf):
        old = []
        if os.path.exists(path):
            with open(path, newline="", encoding="utf-8") as f:
                old = list(csv.DictReader(f))
        replaced = {keyf(r) for r in new}
        kept = [r for r in old if keyf(r) not in replaced]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(kept + new)
        return len(kept) + len(new)

    total = merge(os.path.join(args.root, "judgments.csv"), J_COLS, rows, lambda r: (r["run_id"], r["judge_id"]))
    merge(os.path.join(args.root, "participants.csv"), P_COLS, people, lambda r: (r["run_id"], r["participant"]))
    print("ingested %d participants, %d ratings into run %r; judgments.csv now has %d rows" % (len(people), len(rows), args.run, total))
    for n, why in bad:
        print("  line %d skipped: %s" % (n, why))
    if people:
        print("  forms used:", ", ".join(sorted({p["form"] for p in people})))
    return 1 if bad and not people else 0


if __name__ == "__main__":
    sys.exit(main())
