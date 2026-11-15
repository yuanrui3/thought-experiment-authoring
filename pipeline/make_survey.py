#!/usr/bin/env python3
"""Build the human survey from vignettes.json.

Writes:
  survey/survey.html            standalone page (send the file, or host it anywhere)
  survey/survey_page.html       the same page as a fragment, for publishing as an Artifact
  pipeline/survey_manifest.json private key: item code -> pair and version, and the forms

The page shows each participant ONE version of every pair, in random order, with
no pair ids, authors, factors, predictions or answer keys anywhere in it. Answers
never leave the browser by themselves: at the end the participant gets a completion
code to send back, which pipeline/ingest_survey.py turns into judgments.csv rows.
"""
import json, os, random, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"   # no i, l, o, 0, 1: safe to read aloud and retype

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=20261115)
ap.add_argument("--form-pairs", type=int, default=10, help="number of complementary form pairs")
args = ap.parse_args()

doc = json.load(open(os.path.join(ROOT, "vignettes.json"), encoding="utf-8"))
pairs = doc["pairs"]
rng = random.Random(args.seed)

# opaque two-character item codes
codes = set()
while len(codes) < 2 * len(pairs):
    codes.add(rng.choice(ALPHABET) + rng.choice(ALPHABET))
codes = sorted(codes)
rng.shuffle(codes)
items, key = {}, {}
for p in pairs:
    for v in ("A", "B"):
        c = codes.pop()
        key[c] = {"pair_id": p["pair_id"], "version": v}
        items[c] = {"t": p["versions"][v]["text"], "q": p["judgment_question"]["text"],
                    "l1": p["judgment_question"]["label_min"], "l7": p["judgment_question"]["label_max"],
                    "c": p["comprehension_question"]["text"], "o": p["comprehension_question"]["options"]}
code_of = {(k["pair_id"], k["version"]): c for c, k in key.items()}

# forms: each gives one version of every pair; forms come in complementary pairs so that
# handing out f01, f02, f03, ... in turn keeps the two versions of every pair balanced
forms = {}
n = 0
for _ in range(args.form_pairs):
    order = [p["pair_id"] for p in pairs]
    rng.shuffle(order)
    gets_a = set(order[: len(order) // 2])
    for flip in (False, True):
        n += 1
        forms["f%02d" % n] = [code_of[(p["pair_id"], "A" if ((p["pair_id"] in gets_a) != flip) else "B")] for p in pairs]

manifest = {"protocol": "survey-v1", "seed": args.seed, "items": key, "forms": forms,
            "code_format": "TE1-<participant>-<form>-<background>-<answers>-<check>; each answer is item code (2) + rating (1) + option (1) + seconds in base 36 (2)"}
json.dump(manifest, open(os.path.join(HERE, "survey_manifest.json"), "w"), indent=1)

TEMPLATE = open(os.path.join(HERE, "survey_template.html"), encoding="utf-8").read()
page = (TEMPLATE.replace("/*__ITEMS__*/{}", json.dumps(items, ensure_ascii=False))
                .replace("/*__FORMS__*/{}", json.dumps(forms))
                .replace("__N_ITEMS__", str(len(pairs))))
assert "__ITEMS__" not in page and "__FORMS__" not in page
os.makedirs(os.path.join(ROOT, "survey"), exist_ok=True)
open(os.path.join(ROOT, "survey", "survey_page.html"), "w", encoding="utf-8").write(page)
full = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '</head>\n<body>\n' + page + "\n</body>\n</html>\n")
open(os.path.join(ROOT, "survey", "survey.html"), "w", encoding="utf-8").write(full)
leak = [w for w in ("pair_id", "au_", "cc_", "nc_", "A_higher", "B_higher", "factor_id", "correct") if w in page]
print("survey: %d items, %d forms, %d KB | words that would leak the design: %s" % (len(items), len(forms), len(full) // 1024, leak or "none"))
