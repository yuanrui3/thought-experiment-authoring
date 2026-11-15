#!/usr/bin/env python3
"""Assemble vignettes.json from the authors' raw output, the control pairs and
the auditor-calibration pairs. Pure data shaping: no text is edited."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FACTORS = [
    {"factor_id": "intent_accident", "name": "Intention vs. accident",
     "description": "Whether a person brings about an outcome on purpose or by accident; the physical act and the outcome are held fixed."},
    {"factor_id": "doing_allowing", "name": "Doing vs. allowing",
     "description": "Whether a person actively brings about an outcome or merely allows it when they could have prevented it; outcome, knowledge, motive and ease of acting otherwise are held fixed."},
    {"factor_id": "knowledge_luck", "name": "Knowledge vs. lucky true belief",
     "description": "Whether a true, well-supported belief is true in the normal way or only by luck; the belief, its truth and the evidence as the person sees it are held fixed."},
    {"factor_id": "moral_luck", "name": "Moral luck (outcome luck)",
     "description": "Whether one and the same choice, made with the same knowledge and risk, happens to turn out harmlessly or harmfully for reasons outside the person's control."},
    {"factor_id": "norm_causation", "name": "Norm violation and causal judgment",
     "description": "Whether a person's contribution to an outcome broke a rule or was permitted, with the physical contribution held fixed; the judgment is how much that person caused the outcome."},
    {"factor_id": "null", "name": "Null control",
     "description": "An incidental detail that should not matter (control pairs only)."},
]

WORD_LIMIT = 150


def wc(text):
    return len(text.split())


def shape(p, pair_id, pair_type, author):
    out = {
        "pair_id": pair_id,
        "pair_type": pair_type,
        "factor_id": p["factor_id"],
        "author": author,
        "title": p["title"],
        "versions": {
            "A": {"text": p["version_a"].strip(), "word_count": wc(p["version_a"])},
            "B": {"text": p["version_b"].strip(), "word_count": wc(p["version_b"])},
        },
        "intended_difference": p["intended_difference"],
        "judgment_question": {
            "text": p["judgment_question"].strip(), "scale_min": 1, "scale_max": 7,
            "label_min": p["scale_label_1"].strip(), "label_max": p["scale_label_7"].strip(),
        },
        "comprehension_question": {
            "text": p["comprehension_question"].strip(),
            "options": {"a": p["option_a"].strip(), "b": p["option_b"].strip(), "c": p["option_c"].strip()},
            "correct": {"A": p["correct_option_version_a"], "B": p["correct_option_version_b"]},
        },
    }
    if "predicted_direction" in p:
        out["prediction"] = {"direction": p["predicted_direction"], "size": p["predicted_size"],
                             "rationale": p.get("prediction_rationale", "")}
    for k in ("originality_note", "reference", "null_detail", "planted_confound", "planted_keywords"):
        if k in p:
            out[k] = p[k]
    # format compliance, checked mechanically
    problems = []
    for v in ("A", "B"):
        if out["versions"][v]["word_count"] > WORD_LIMIT:
            problems.append("version %s has %d words (limit %d)" % (v, out["versions"][v]["word_count"], WORD_LIMIT))
    if "prediction" in out:
        d, s = out["prediction"]["direction"], out["prediction"]["size"]
        if (d == "none") != (s == "none"):
            problems.append("prediction is inconsistent: direction=%s, size=%s" % (d, s))
    out["format_problems"] = problems
    return out


def main():
    raw = json.load(open(os.path.join(HERE, "raw", "authoring_output.json")))
    controls = json.load(open(os.path.join(HERE, "controls.json")))
    calib = json.load(open(os.path.join(HERE, "audit_calibration.json")))
    pairs = []
    tiers = ["haiku", "sonnet", "opus", "fable"]
    for tier in tiers:
        label = "author:%s" % tier
        prov = raw["provenance"][label]
        served = prov["served"][0] if prov["served"] else ""
        author = {"type": "llm", "vendor": "anthropic", "tier": tier, "model": served,
                  "author_id": "anthropic/%s" % served, "requested_alias": tier,
                  "tool_calls": prov["tool_calls"], "authoring_run": "pilot-2026-11-14"}
        got = raw["authors"][label]["pairs"]
        seen = set()
        for p in got:
            if p["factor_id"] in seen:
                raise SystemExit("duplicate factor from %s: %s" % (tier, p["factor_id"]))
            seen.add(p["factor_id"])
            pairs.append(shape(p, "au_%s_%s" % (tier, p["factor_id"]), "authored", author))
        missing = {f["factor_id"] for f in FACTORS if f["factor_id"] != "null"} - seen
        if missing:
            raise SystemExit("%s is missing factors: %s" % (tier, missing))
    builder = {"type": "researcher", "vendor": "anthropic", "author_id": "pilot-builder",
               "note": "Control pairs written by the pilot's builder, an AI system; not an evaluated author."}
    for p in controls["pairs"]:
        pairs.append(shape(p, p["pair_id"], p["pair_type"], builder))
    calib_pairs = [shape(p, p["pair_id"], p["pair_type"], builder) for p in calib["pairs"]]

    doc = {
        "schema_version": "0.1",
        "benchmark": "thought-experiment-authoring",
        "release": "pilot-2026-11-14",
        "language": "en",
        "task": {
            "word_limit_per_version": WORD_LIMIT,
            "word_count_rule": "whitespace-separated tokens",
            "judgment_scale": [1, 7],
            "effect_definition": "mean rating of version A minus mean rating of version B, in scale points",
            "size_bins": {"none": "|diff| < 0.5", "small": "0.5 <= |diff| < 1.5", "large": "|diff| >= 1.5"},
        },
        "factors": FACTORS,
        "pairs": pairs,
        "audit_calibration_pairs": calib_pairs,
    }
    path = os.path.join(ROOT, "vignettes.json")
    json.dump(doc, open(path, "w"), indent=1, ensure_ascii=False)
    print("wrote", path, "| pairs:", len(pairs), "| calibration pairs:", len(calib_pairs))
    for p in pairs + calib_pairs:
        flag = ("  !! " + "; ".join(p["format_problems"])) if p["format_problems"] else ""
        print("  %-28s %-16s A=%3d B=%3d%s" % (p["pair_id"], p["pair_type"], p["versions"]["A"]["word_count"], p["versions"]["B"]["word_count"], flag))


if __name__ == "__main__":
    main()
