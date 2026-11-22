#!/usr/bin/env python3
"""Builds results.html from out/results.json (called by score.py; can also run alone).

Reads two optional hand-written files: commentary.json (headline findings and
per-pair diagnoses) and METHODS.md (rendered at the bottom of the page).
If pipeline/compare_vendor_panels.py has been run, it also shows a second judge
panel from another vendor side by side with the main one (out/vendor_comparison.csv
and out/vendor_comparison_summary.json), provided those files match this run; and
likewise the persona panel from pipeline/compare_persona_panel.py.
"""
import csv, difflib, html, json, math, os, re

TIER_ORDER = ["haiku", "sonnet", "opus", "fable"]
FACTOR_ORDER = ["intent_accident", "doing_allowing", "knowledge_luck", "moral_luck", "norm_causation"]


def esc(s):
    return html.escape(str(s), quote=True)


def sgn(x, n=2):
    return ("%+." + str(n) + "f") % x


def short_group(g):
    m = re.search(r"claude-([a-z]+)", g)
    return m.group(1) if m else g.split("/")[-1]


def pred_text(pr):
    if not pr:
        return ""
    if pr["direction"] == "none":
        return "no difference"
    return "%s higher, %s" % (pr["direction"][0], pr["size"])


def obs_text(o):
    if o["direction"] == "none":
        return "no difference"
    if o["direction"] == "unclear":
        return "not confirmed (%s-sized gap)" % o["size"]
    return "%s higher, %s" % (o["direction"][0], o["size"])


def pred_zone(pr, rules):
    """Range of the A-minus-B difference that the prediction covers."""
    lo, hi = rules["none_below"], rules["large_from"]
    if pr["direction"] == "none":
        return (-lo, lo)
    rng = (lo, hi) if pr["size"] == "small" else (hi, 6.0)
    return rng if pr["direction"] == "A_higher" else (-rng[1], -rng[0])


def diff_html(a_text, b_text):
    """Both versions with the words that differ marked."""
    a, b = a_text.split(), b_text.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out_a, out_b = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out_a.append(esc(" ".join(a[i1:i2])))
            out_b.append(esc(" ".join(b[j1:j2])))
        else:
            if i2 > i1:
                out_a.append('<mark class="chg">%s</mark>' % esc(" ".join(a[i1:i2])))
            if j2 > j1:
                out_b.append('<mark class="chg">%s</mark>' % esc(" ".join(b[j1:j2])))
    return " ".join(out_a), " ".join(out_b)


# ------------------------------------------------------------------ charts

def forest_svg(R):
    rules = R["rules"]
    pairs = [p for p in R["pairs"] if "effect" in p]
    fac_name = {f["factor_id"]: f["name"] for f in R["factors"]}
    groups = [("Classic controls: a known human result should reappear", [p for p in pairs if p["pair_type"] == "control_classic"]),
              ("Null controls: nothing should change", [p for p in pairs if p["pair_type"] == "control_null"])]
    for f in FACTOR_ORDER:
        rows = [p for p in pairs if p["pair_type"] == "authored" and p["factor_id"] == f]
        rows.sort(key=lambda p: TIER_ORDER.index(p["author_tier"]) if p["author_tier"] in TIER_ORDER else 9)
        if rows:
            groups.append(("Authored: " + fac_name.get(f, f), rows))
    W, X0, X1, RH, HH = 1000, 318, 742, 24, 30
    xs = lambda v: X0 + (max(-6, min(6, v)) + 6) / 12 * (X1 - X0)
    n_rows = sum(len(g[1]) for g in groups)
    H = 44 + n_rows * RH + len(groups) * HH + 40
    o = ['<svg class="forest" viewBox="0 0 %d %d" role="img" aria-label="Difference in mean rating between version A and version B for every pair, with 95%% intervals and each author\'s predicted range" preserveAspectRatio="xMinYMin meet">' % (W, H)]
    top, bottom = 34, H - 34
    for t in range(-6, 7, 2):
        o.append('<line class="%s" x1="%.1f" x2="%.1f" y1="%d" y2="%d"/>' % ("zero" if t == 0 else "grid", xs(t), xs(t), top, bottom))
        o.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (xs(t), top - 10, ("%+d" % t) if t else "0"))
        o.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (xs(t), bottom + 16, ("%+d" % t) if t else "0"))
    o.append('<text class="axis" x="%.1f" y="%d" text-anchor="middle">B rated higher  ←  difference in mean rating (A minus B), scale points  →  A rated higher</text>' % ((X0 + X1) / 2, H - 2))
    o.append('<text class="colhead" x="%d" y="%d">difference [95%% interval]</text>' % (X1 + 18, top - 10))
    o.append('<text class="colhead" x="%d" y="%d" text-anchor="end">prediction</text>' % (W - 4, top - 10))
    y = top + 4
    for title, rows in groups:
        o.append('<text class="grp" x="4" y="%d">%s</text>' % (y + 19, esc(title)))
        y += HH
        for p in rows:
            e, pr, ob = p["effect"], p["prediction"], p["observed"]
            cy = y + RH / 2
            label = p["title"] if p["pair_type"] != "authored" else "%s · %s" % (p["author_tier"], p["title"])
            if len(label) > 46:
                label = label[:45].rstrip() + "…"
            z0, z1 = pred_zone(pr, rules)
            ps = p["prediction_result"]
            verdict = "hit" if (ps["direction_hit"] and ps["size_hit"]) else ("direction only" if ps["direction_hit"] else ("size only" if ps["size_hit"] else "miss"))
            tip = {"t": label, "p": pred_text(pr), "o": obs_text(ob), "e": "%s [%s, %s]" % (sgn(e["effect"]), sgn(e["ci_low"]), sgn(e["ci_high"])),
                   "a": "%.2f" % e["mean_a"], "b": "%.2f" % e["mean_b"], "g": "%d of %d" % (e["groups_same_sign"], e["groups_total"]), "v": verdict}
            o.append('<g class="row" tabindex="0" data-tip="%s">' % esc(json.dumps(tip)))
            o.append('<rect class="hit" x="0" y="%.1f" width="%d" height="%d"/>' % (y, W, RH))
            o.append('<text class="lab" x="14" y="%.1f">%s</text>' % (cy + 4, esc(label)))
            o.append('<rect class="zone" x="%.1f" y="%.1f" width="%.1f" height="14" rx="3"/>' % (xs(z0), cy - 7, xs(z1) - xs(z0)))
            o.append('<line class="ci" x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f"/>' % (xs(e["ci_low"]), xs(e["ci_high"]), cy, cy))
            o.append('<circle class="dot" cx="%.1f" cy="%.1f" r="5"/>' % (xs(e["effect"]), cy))
            o.append('<text class="num" x="%d" y="%.1f">%s [%s, %s]</text>' % (X1 + 18, cy + 4, sgn(e["effect"]), sgn(e["ci_low"]), sgn(e["ci_high"])))
            o.append('<text class="num verdict" x="%d" y="%.1f" text-anchor="end">%s</text>' % (W - 4, cy + 4, verdict))
            o.append("</g>")
            y += RH
    o.append("</svg>")
    return "\n".join(o)


def strip_svg(p):
    """Every rating for one pair: one row per judge group, version A above version B."""
    e = p["effect"]
    groups = sorted(e["groups"], key=lambda g: TIER_ORDER.index(short_group(g)) if short_group(g) in TIER_ORDER else 9)
    W, X0, X1, RH = 460, 96, 440, 44
    H = 30 + len(groups) * RH + 22
    xs = lambda v: X0 + (v - 1) / 6 * (X1 - X0)
    o = ['<svg class="strip" viewBox="0 0 %d %d" role="img" aria-label="All ratings for this pair by judge model and version">' % (W, H)]
    for t in range(1, 8):
        o.append('<line class="grid" x1="%.1f" x2="%.1f" y1="20" y2="%d"/>' % (xs(t), xs(t), H - 22))
        o.append('<text class="tick" x="%.1f" y="%d" text-anchor="middle">%d</text>' % (xs(t), H - 6, t))
    y = 24
    for g in groups:
        pg = e["per_group"][g]
        o.append('<text class="lab" x="0" y="%.1f">%s</text>' % (y + RH / 2 + 4, esc(short_group(g))))
        for cls, key, yy, tag in (("a", "ratings_a", y + 12, "A"), ("b", "ratings_b", y + 30, "B")):
            o.append('<text class="vtag" x="%d" y="%.1f">%s</text>' % (X0 - 26, yy + 4, tag))
            counts = {}
            for r in sorted(pg[key]):
                k = counts.get(r, 0)
                counts[r] = k + 1
            for r, n in counts.items():
                for k in range(n):
                    dx = (k - (n - 1) / 2) * 9.5
                    o.append('<circle class="dot %s" cx="%.1f" cy="%.1f" r="4.5"><title>%s, version %s: rated %d</title></circle>' % (cls, xs(r) + dx, yy, esc(short_group(g)), tag, r))
        y += RH
    o.append("</svg>")
    return "\n".join(o)


# ------------------------------------------------------------------ small markdown renderer (for METHODS.md)

def md_inline(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r"\1 (<code>\2</code>)", s)
    return s


def md_to_html(text):
    out, para, lst = [], [], None

    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>%s</p>" % md_inline(" ".join(para))); para = []
        if lst:
            out.append("<%s>%s</%s>" % (lst[0], "".join("<li>%s</li>" % md_inline(i) for i in lst[1]), lst[0])); lst = None

    for line in text.splitlines():
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush(); lvl = min(len(m.group(1)) + 1, 5)
            out.append("<h%d>%s</h%d>" % (lvl, md_inline(m.group(2)), lvl)); continue
        m = re.match(r"^\s*(?:[-*]|\d+\.)\s+(.*)$", line)
        if m:
            kind = "ol" if re.match(r"^\s*\d+\.", line) else "ul"
            if para:
                out.append("<p>%s</p>" % md_inline(" ".join(para))); para = []
            if lst and lst[0] != kind:
                flush()
            if not lst:
                lst = (kind, [])
            lst[1].append(m.group(1)); continue
        if not line.strip():
            flush(); continue
        if lst and line.startswith("  "):
            lst[1][-1] += " " + line.strip(); continue
        para.append(line.strip())
    flush()
    return "\n".join(out)


# ------------------------------------------------------------------ page pieces

def chip(text, kind=""):
    return '<span class="chip %s">%s</span>' % (kind, esc(text))


def flag_chips(p):
    out = []
    for f in p.get("flags", []):
        bad = any(k in f for k in ("severe", "re-skin", "opposite", "voided", "format", "low comprehension"))
        out.append(chip(("✕ " if bad else "! ") + f, "bad" if bad else "warn"))
    return " ".join(out)


def pair_label(p):
    if p["pair_type"] == "authored":
        return "%s · %s" % (p["author_tier"], p["title"])
    return p["title"]


def pair_card(p, R, rank_label, note):
    fac = {f["factor_id"]: f["name"] for f in R["factors"]}
    e, pr, ob, au = p["effect"], p["prediction"], p["observed"], p.get("audit")
    a_html, b_html = diff_html(p["versions"]["A"]["text"], p["versions"]["B"]["text"])
    cq, jq = p["comprehension_question"], p["judgment_question"]
    o = ['<article class="card" id="%s">' % esc(p["pair_id"])]
    o.append('<header><div><p class="eyebrow">%s</p><h3>%s</h3><p class="sub">%s · factor: %s</p></div>' % (
        esc(rank_label), esc(p["title"]),
        esc("written by the %s author" % p["author_tier"] if p["pair_type"] == "authored" else "control written by the builder"),
        esc(fac.get(p["factor_id"], p["factor_id"]))))
    if p.get("composite") is not None:
        o.append('<div class="score"><span class="big">%.0f</span><span class="of">/ 100</span></div>' % p["composite"])
    o.append("</header>")
    o.append('<div class="versions"><div><h4>Version A <span class="wc">%d words</span></h4><p class="vig">%s</p></div><div><h4>Version B <span class="wc">%d words</span></h4><p class="vig">%s</p></div></div>' % (
        p["versions"]["A"]["word_count"], a_html, p["versions"]["B"]["word_count"], b_html))
    o.append('<p class="q"><strong>Judgment question.</strong> %s <span class="muted">(1 = %s; 7 = %s)</span></p>' % (esc(jq["text"]), esc(jq["label_min"]), esc(jq["label_max"])))
    o.append('<p class="q"><strong>Comprehension question.</strong> %s <span class="muted">a) %s · b) %s · c) %s. Key: A = %s, B = %s. Answered correctly by %.0f%% of judges.</span></p>' % (
        esc(cq["text"]), esc(cq["options"]["a"]), esc(cq["options"]["b"]), esc(cq["options"]["c"]), cq["correct"]["A"], cq["correct"]["B"], 100 * p["comprehension"]["accuracy"]))
    o.append('<div class="result"><div class="rtext">')
    o.append('<p><strong>Predicted:</strong> %s. <strong>Observed:</strong> %s. Mean rating %.2f for A and %.2f for B, a difference of %s (95%% interval %s to %s); %d of %d judge models agree on the sign.</p>' % (
        esc(pred_text(pr)), esc(obs_text(ob)), e["mean_a"], e["mean_b"], sgn(e["effect"]), sgn(e["ci_low"]), sgn(e["ci_high"]), e["groups_same_sign"], e["groups_total"]))
    if pr.get("rationale"):
        o.append('<p class="muted"><strong>Author\'s reasoning:</strong> %s</p>' % esc(pr["rationale"]))
    c = p["components"]
    if au:
        o.append('<p class="comp">Prediction %.2f · Confounds %.2f (severity %d of 3; auditors gave %s) · Originality %.2f (level %d of 3; auditors gave %s) · Comprehension %.2f · %d of %d words changed</p>' % (
            c["prediction"], c["confounds"], au["confound_severity"], ", ".join(str(x) for x in au["confound_severity_all"]),
            c["originality"], au["originality"], ", ".join(str(x) for x in au["originality_all"]), c["comprehension"],
            p["text"]["words_changed"], max(p["text"]["words_a"], p["text"]["words_b"])))
    if p.get("flags"):
        o.append('<p class="chips">%s</p>' % flag_chips(p))
    o.append('</div><figure class="stripwrap"><figcaption>Every rating, by judge model. <span class="key a">●</span> version A <span class="key b">●</span> version B</figcaption>%s</figure></div>' % strip_svg(p))
    if au:
        diffs, cases, qprobs = [], [], []
        for d in au["detail"]:
            who = short_group(d["auditor"])
            for x in d["other_differences"]:
                diffs.append("<li>%s <span class='muted'>(%s auditor)</span></li>" % (esc(x), esc(who)))
            if d["closest_known_case"] and d["closest_known_case"].strip().lower() not in ("none", "none.", ""):
                cases.append("%s (%s)" % (d["closest_known_case"], who))
            if d["question_problems"].strip():
                qprobs.append("<li>%s <span class='muted'>(%s auditor)</span></li>" % (esc(d["question_problems"]), esc(who)))
        o.append('<details><summary>What the auditors reported</summary>')
        o.append("<p><strong>Other differences between the versions:</strong></p><ul>%s</ul>" % ("".join(diffs) or "<li>None reported.</li>"))
        o.append("<p><strong>Closest known case named:</strong> %s</p>" % (esc("; ".join(cases)) or "none"))
        if qprobs:
            o.append("<p><strong>Problems with the questions:</strong></p><ul>%s</ul>" % "".join(qprobs))
        o.append("</details>")
    if note:
        o.append('<div class="diagnosis"><h4>Diagnosis</h4>%s</div>' % "".join("<p>%s</p>" % md_inline(x) for x in (note if isinstance(note, list) else [note])))
    o.append("</article>")
    return "\n".join(o)


def verdict_text(v):
    d, z = v.split("/")
    return obs_text({"direction": d, "size": z})


def vendor_section(R, root, P, fac):
    """Side-by-side panel from another vendor, or [] if the comparison files are missing or stale."""
    cpath = os.path.join(root, "out", "vendor_comparison.csv")
    spath = os.path.join(root, "out", "vendor_comparison_summary.json")
    if not (os.path.exists(cpath) and os.path.exists(spath)):
        return [], None
    rows = {r["pair_id"]: r for r in csv.DictReader(open(cpath, encoding="utf-8"))}
    summ = json.load(open(spath, encoding="utf-8"))
    stale = [p["pair_id"] for p in P if p["pair_id"] not in rows or abs(float(rows[p["pair_id"]]["claude_effect"]) - p["effect"]["effect"]) > 1e-6]
    if stale:
        print("vendor comparison skipped: out/vendor_comparison.csv does not match this run (rerun pipeline/compare_vendor_panels.py)")
        return [], None
    other = summ.get("other_label", "Gemini")
    models = summ.get("other_models", [])
    S = []
    S.append('<section id="vendors"><h2>A second judge panel: %s</h2>' % esc(other))
    S.append('<p class="prose">To see how much the results depend on the judges, %s (%s) rated the same 30 pairs. They used the same design (one version of each pair per judge, five repeats, two arms) and the Claude judges\' prompt word for word. The pairs are scored here three ways with the same rules and the same audits: by the Claude panel alone (everything above), by the %s panel alone, and with the two vendors as two judge groups. In that last scoring each vendor counts once and a gap is confirmed only if both find it. None of these panels has been checked against people on these pairs.</p>' % (
        esc(other), esc(", ".join(models)) or "two models", esc(other)))
    n = summ["pairs"]
    S.append('<div class="tiles">')
    S.append('<div class="tile"><p class="tl">Same direction</p><p class="tv">%d <span>of %d pairs</span></p><p class="tn">Including pairs both call “no difference”</p></div>' % (summ["directions_agree"], n))
    S.append('<div class="tile"><p class="tl">Same verdict</p><p class="tv">%d <span>of %d pairs</span></p><p class="tn">Direction and size both match; authored pairs %d of %d</p></div>' % (summ["verdicts_agree"], n, summ["authored_verdicts_agree"], summ["authored"]))
    S.append('<div class="tile"><p class="tl">Agreement on effect sizes</p><p class="tv">%.2f</p><p class="tn">Correlation of A − B across all pairs</p></div>' % summ["effect_correlation_all"])
    S.append('<div class="tile"><p class="tl">Mean |A − B|, authored pairs</p><p class="tv">%.2f <span>vs %.2f</span></p><p class="tn">Claude vs %s</p></div>' % (
        summ["mean_abs_effect_authored"]["claude"], summ["mean_abs_effect_authored"]["gemini"], esc(other)))
    S.append('</div>')

    # authors under each scoring
    cols = [("claude", "Claude panel (above)"), ("gemini", "%s panel" % other), ("vendor_groups", "Two vendors, one group each"), ("six_models", "All six models, one group each")]
    tops = {k: max(summ["authors"], key=lambda t: float(summ["authors"][t][k]["mean_composite"])) for k, _ in cols}
    S.append('<h3>Authors under each panel</h3><div class="scroll"><table class="data"><thead><tr><th>Author</th>%s</tr></thead><tbody>' % "".join(
        '<th class="n">%s</th>' % esc(lab) for _, lab in cols))
    for t in sorted(summ["authors"], key=lambda t: TIER_ORDER.index(t) if t in TIER_ORDER else 9):
        cells = []
        for k, _ in cols:
            a = summ["authors"][t][k]
            cells.append('<td class="n%s">%.1f<br><span class="muted">%s of 5 fully right</span></td>' % (
                " strong" if tops[k] == t else "", float(a["mean_composite"]), a["full_hits"]))
        S.append('<tr><td>%s</td>%s</tr>' % (esc(t), "".join(cells)))
    S.append('</tbody></table></div><p class="note">Mean composite score; bold marks first place under that panel. “Fully right” means direction and size both match the prediction. Four of the six models are Claude, so the six-model scoring mostly repeats the Claude panel\'s verdicts.</p>')

    # pairs side by side
    S.append('<h3>Every pair, side by side</h3><div class="scroll"><table class="data pairs"><thead><tr><th>Pair</th><th>Predicted</th><th class="n">Claude: A − B [95%% interval]</th><th>Claude verdict</th><th class="n">%s: A − B [95%% interval]</th><th>%s verdict</th><th>Two vendors</th><th class="n">Prediction score: Claude / %s / two vendors</th></tr></thead><tbody>' % (
        esc(other), esc(other), esc(other)))
    order = sorted([p for p in P if p["pair_type"] == "authored"], key=lambda p: (FACTOR_ORDER.index(p["factor_id"]) if p["factor_id"] in FACTOR_ORDER else 9,
                                                                                   TIER_ORDER.index(p["author_tier"]) if p["author_tier"] in TIER_ORDER else 9))
    order += [p for p in P if p["pair_type"] == "control_classic"] + [p for p in P if p["pair_type"] == "control_null"]
    last = None
    for p in order:
        grp = fac.get(p["factor_id"], "") if p["pair_type"] == "authored" else {"control_classic": "Classic controls", "control_null": "Null controls"}[p["pair_type"]]
        if grp != last:
            S.append('<tr class="grouprow"><th colspan="8">%s</th></tr>' % esc(grp))
            last = grp
        r = rows[p["pair_id"]]
        differ = r["vendors_agree"] != "True"
        S.append('<tr%s><td>%s%s</td><td>%s</td><td class="n">%s %s</td><td>%s</td><td class="n">%s %s</td><td>%s</td><td>%s</td><td class="n">%s / %s / %s</td></tr>' % (
            ' class="differ"' if differ else "", esc(pair_label(p)), ('<br>' + chip("panels differ", "warn")) if differ else "",
            esc(pred_text(p["prediction"])),
            sgn(float(r["claude_effect"])), esc(r["claude_ci"]), esc(verdict_text(r["claude_verdict"])),
            sgn(float(r["gemini_effect"])), esc(r["gemini_ci"]), esc(verdict_text(r["gemini_verdict"])),
            esc(verdict_text(r["vendor_groups_verdict"])),
            r["claude_prediction_score"], r["gemini_prediction_score"], r["vendor_groups_prediction_score"]))
    S.append('</tbody></table></div><p class="note">Effects are mean rating of version A minus version B on the 1–7 scale. A verdict needs a gap of at least %.1f points whose 95%% interval excludes zero and on which at least 75%% of a panel\'s models agree; otherwise it is “no difference”, or “not confirmed” if the models split. The full table is <code>out/vendor_comparison.csv</code>.</p>' % R["rules"]["none_below"])
    return S, summ


def prediction_rule_note(rules):
    if rules.get("prediction_rule") != "distance":
        return ""
    return ('<p class="prose"><strong>How prediction is scored.</strong> Full credit when the measured gap falls inside the range the prediction names '
            '(no difference: under %.1f points either way; small: %.1f to %.1f; large: %.1f or more), falling to nothing at %.1f points outside it. '
            'A pair that is supposed to show a gap, an authored pair or a classic control, earns nothing unless its gap is confirmed in the predicted '
            'direction, so predicting “no difference” cannot pay off for a pair the author designed to show one. This rule replaced the original one '
            '(half for direction, half for the size class) on 22 November, after the public human data showed that the original rule rewarded '
            'caution; where the two differ, the original score is shown in grey.</p>' % (
                rules["none_below"], rules["none_below"], rules["large_from"], rules["large_from"], rules["distance_scale"]))


def prediction_cell(p, rules):
    c = p["components"]
    if c["prediction"] is None:
        return ""
    out = "%.2f" % c["prediction"]
    by = p.get("prediction_scores_by_rule")
    if rules.get("prediction_rule") == "distance" and by and by.get("classes") is not None:
        old = 0.0 if (p.get("audit") or {}).get("factor_not_realized") else by["classes"]
        if abs(old - c["prediction"]) > 1e-9:
            out += '<br><span class="muted">was %.2f</span>' % old
    return out


def panels_pointer(vsumm, psumm):
    parts = []
    if vsumm:
        parts.append('a panel from %s (<a href="#vendors">compared here</a>)' % esc(vsumm.get("other_label", "another vendor")))
    if psumm:
        parts.append('Claude judges answering as described participants (<a href="#personas">compared here</a>)')
    if len(parts) == 2:
        return "Two other panels, %s and %s, both put a different author first." % tuple(parts)
    return "A second panel, %s, changes which author comes first." % parts[0]


def persona_section(R, root, P, fac):
    """The pilot rejudged by Claude models answering as described participants, or [] if the files are missing or stale."""
    cpath = os.path.join(root, "out", "persona_comparison.csv")
    spath = os.path.join(root, "out", "persona_comparison_summary.json")
    if not (os.path.exists(cpath) and os.path.exists(spath)):
        return [], None
    rows = {r["pair_id"]: r for r in csv.DictReader(open(cpath, encoding="utf-8"))}
    summ = json.load(open(spath, encoding="utf-8"))
    if any(p["pair_id"] not in rows or abs(float(rows[p["pair_id"]]["published_effect"]) - p["effect"]["effect"]) > 1e-6 for p in P):
        print("persona comparison skipped: out/persona_comparison.csv does not match this run (rerun pipeline/compare_persona_panel.py)")
        return [], None
    judges = [short_group(m) for m in summ["judge_models"]]
    n_judges = len(judges)
    S = ['<section id="personas"><h2>Judges answering as participants</h2>']
    S.append('<p class="prose">On public data with human ratings, model judges vary far less than people do, and giving each judge a described participant to answer as (an age, a job, politics, religiosity and a habit in using rating scales) made a panel behave more like people (<code>reports/Fixing the panel\'s overconfidence.md</code>). Here the pilot is rejudged that way: the same batches, versions and prompt as the panel above, each judge with its own persona. It is compared with the panel above restricted to the same %s judge models (%s); %s. A persona panel is still not people.</p>' % (
        {3: "three", 4: "four"}.get(n_judges, str(n_judges)), esc(", ".join(judges)),
        "Fable's persona judges have not run yet, so with three judge groups a gap counts only if all three agree" if "fable" not in judges else "all four judge models are included"))
    sp_o, sp_p = summ["spread_within_model"]["original"], summ["spread_within_model"]["persona"]
    widest = max(sp_p, key=lambda m: sp_p[m] - sp_o.get(m, 0))
    S.append('<div class="tiles">')
    S.append('<div class="tile"><p class="tl">Spread within one model, %s</p><p class="tv">%.2f <span>from %.2f</span></p><p class="tn">SD of ratings of one version; %s</p></div>' % (
        esc(short_group(widest)), sp_p[widest], sp_o[widest], esc("; ".join("%s %.2f → %.2f" % (short_group(m), sp_o[m], sp_p[m]) for m in sp_p if m != widest))))
    S.append('<div class="tile"><p class="tl">Verdicts that change</p><p class="tv">%d <span>of %d pairs</span></p><p class="tn">Effects still correlate %.2f with the panel above</p></div>' % (
        summ["verdicts_changed"], len(rows), summ["effect_correlation_with_original"]))
    S.append('<div class="tile"><p class="tl">Classic controls reproduced</p><p class="tv">%d <span>of %d</span></p><p class="tn">Panel above, same judges: %d; null controls with a gap: %d</p></div>' % (
        summ["classic_controls_in_expected_direction"]["persona"], sum(1 for r in rows.values() if r["pair_type"] == "control_classic"),
        summ["classic_controls_in_expected_direction"]["original_same_models"], summ["null_controls_with_a_gap"]["persona"]))
    if "agrees_with_gemini" in summ:
        S.append('<div class="tile"><p class="tl">Same verdict as the Gemini panel</p><p class="tv">%d <span>of %d</span></p><p class="tn">Panel above, same judges: %d</p></div>' % (
            summ["agrees_with_gemini"]["persona"], len(rows), summ["agrees_with_gemini"]["original_same_models"]))
    S.append('</div>')
    cols = [("published", "Panel above (4 judge models)"), ("original_same_models", "Panel above, same %d judge models" % n_judges),
            ("persona", "With personas (%d judge models)" % n_judges)]
    if any("gemini" in v for v in summ["authors"].values()):
        cols.append(("gemini", "Gemini panel"))
    tops = {k: max(summ["authors"], key=lambda t: float(summ["authors"][t][k]["mean_composite"])) for k, _ in cols}
    S.append('<h3>Authors under each panel</h3><div class="scroll"><table class="data"><thead><tr><th>Author</th>%s</tr></thead><tbody>' % "".join(
        '<th class="n">%s</th>' % esc(lab) for _, lab in cols))
    for t in sorted(summ["authors"], key=lambda t: TIER_ORDER.index(t) if t in TIER_ORDER else 9):
        S.append('<tr><td>%s</td>%s</tr>' % (esc(t), "".join('<td class="n%s">%.1f<br><span class="muted">%s of 5 fully right</span></td>' % (
            " strong" if tops[k] == t else "", float(summ["authors"][t][k]["mean_composite"]), summ["authors"][t][k]["full_hits"]) for k, _ in cols)))
    S.append('</tbody></table></div><p class="note">Mean composite score; bold marks first place under that panel. Confound and originality grades are the same audits throughout; only the judges change.</p>')
    changed = [r for r in rows.values() if r["persona_changes_verdict"] == "True"]
    if changed:
        by_id = {p["pair_id"]: p for p in P}
        S.append('<h3>Verdicts that change</h3><div class="scroll"><table class="data pairs"><thead><tr><th>Pair</th><th>Predicted</th><th class="n">Same judges, no personas: A − B</th><th>Verdict</th><th class="n">With personas: A − B</th><th>Verdict</th><th>Gemini verdict</th><th class="n">Prediction score, before → after</th></tr></thead><tbody>')
        for r in sorted(changed, key=lambda r: (["authored", "control_classic", "control_null"].index(r["pair_type"]), r["pair_id"])):
            p = by_id[r["pair_id"]]
            S.append('<tr><td>%s</td><td>%s</td><td class="n">%s<br><span class="muted">%s models agree</span></td><td>%s</td><td class="n">%s<br><span class="muted">%s models agree</span></td><td>%s</td><td>%s</td><td class="n">%s → %s</td></tr>' % (
                esc(pair_label(p)), esc(pred_text(p["prediction"])),
                sgn(float(r["original_same_models_effect"])), esc(r["original_same_models_models_agreeing"].replace("/", " of ")), esc(verdict_text(r["original_same_models_verdict"])),
                sgn(float(r["persona_effect"])), esc(r["persona_models_agreeing"].replace("/", " of ")), esc(verdict_text(r["persona_verdict"])),
                esc(verdict_text(r["gemini_verdict"])) if "gemini_verdict" in r else "–",
                r["original_same_models_prediction_score"], r["persona_prediction_score"]))
        S.append('</tbody></table></div><p class="note">Every pair under each panel is in <code>out/persona_comparison.csv</code>. The persona judges read the prompt from a file at the default effort level; the judges above got it inline at low effort. So this comparison is not about personas alone. The calibration test, where both conditions were delivered the same way, is.</p>')
    return S, summ


def build(R, root):
    rules = R["rules"]
    comm = {}
    cpath = os.path.join(root, "commentary.json")
    if os.path.exists(cpath):
        comm = json.load(open(cpath, encoding="utf-8"))
    methods_html = ""
    mpath = os.path.join(root, "METHODS.md")
    if os.path.exists(mpath):
        methods_html = md_to_html(open(mpath, encoding="utf-8").read())

    P = [p for p in R["pairs"] if "effect" in p]
    authored = [p for p in P if p["pair_type"] == "authored"]
    fac = {f["factor_id"]: f["name"] for f in R["factors"]}
    panel, data = R["panel"], R["data"]
    have_audit = all(p.get("composite") is not None for p in authored)
    ranked = sorted(authored, key=lambda p: (-(p["composite"] if p["composite"] is not None else -1), p["pair_id"]))
    sc = lambda p: round(p["composite"], 1) if p["composite"] is not None else -1
    best = [p for p in ranked if sc(p) >= sc(ranked[min(2, len(ranked) - 1)])]          # ties at the cut are all shown
    worst = list(reversed([p for p in ranked if sc(p) <= sc(ranked[max(len(ranked) - 3, 0)])]))
    comp_all = sum(p["comprehension"]["accuracy"] * (p["effect"]["n_a"] + p["effect"]["n_b"]) for p in P) / sum(p["effect"]["n_a"] + p["effect"]["n_b"] for p in P)
    n_models = len(data["judge_groups"])
    vend, vsumm = vendor_section(R, root, P, fac)
    pers, psumm = persona_section(R, root, P, fac)

    S = []
    # ---- header
    S.append('<header class="top"><p class="eyebrow">Pilot results · %s</p><h1>Thought-experiment authoring</h1>' % esc(comm.get("date", R["release"])))
    S.append('<p class="lede">Can a language model design a philosophical thought experiment that works? Each author model was given one factor, wrote a pair of short scenarios that differ only in that factor, and predicted how readers would judge them. A panel then rated the scenarios, each judge seeing one version only.</p>')
    S.append('<div class="caveat"><strong>What this pilot measures: whether a model can predict how a panel of Claude models will judge its thought experiment. It does not yet show that the pairs work on people.</strong> No human has judged them; a human run is the next step. Until then, read this as a test of the pipeline. Every judge and every author here is a Claude model, so the panel shares the authors\' blind spots. %s%s</div></header>' % (
        md_inline(comm.get("caveat", "Published work finds that language-model panels exaggerate effect sizes and often find effects where people show none.")),
        (" " + panels_pointer(vsumm if vend else None, psumm if pers else None)) if (vend or pers) else ""))

    # ---- panel checks
    sh = panel["split_half_noise"]
    S.append('<section><h2>Did the panel itself behave?</h2><div class="tiles">')
    S.append('<div class="tile"><p class="tl">Classic controls reproduced</p><p class="tv">%d <span>of %d</span></p><p class="tn">Known human direction reappears</p></div>' % (panel["classics_reproduced"], panel["classics_total"]))
    S.append('<div class="tile"><p class="tl">Null controls with a false gap</p><p class="tv">%d <span>of %d</span></p><p class="tn">Largest null difference: %.2f points</p></div>' % (panel["null_false_positives"], panel["nulls_total"], panel["null_max_abs_effect"] or 0))
    S.append('<div class="tile"><p class="tl">Noise floor</p><p class="tv">%s <span>points</span></p><p class="tn">95th percentile gap between random halves of the same scenario</p></div>' % ("%.2f" % sh["p95"] if sh["p95"] is not None else "n/a"))
    S.append('<div class="tile"><p class="tl">Comprehension</p><p class="tv">%.1f<span>%%</span></p><p class="tn">Of %s answers across %d judges</p></div>' % (100 * comp_all, format(data["n_judgments"], ","), data["n_judges"]))
    S.append("</div>")
    if comm.get("panel_note"):
        S.append("".join('<p class="prose">%s</p>' % md_inline(x) for x in comm["panel_note"]))
    S.append("</section>")

    # ---- headline
    if comm.get("headline"):
        S.append('<section><h2>What the pilot shows</h2><ul class="findings">%s</ul></section>' % "".join("<li>%s</li>" % md_inline(x) for x in comm["headline"]))

    # ---- forest
    S.append('<section><h2>Every pair at a glance</h2><p class="prose">Each row is one pair. The dot is the difference between the mean rating of version A and of version B; the line is its 95%% bootstrap interval. The grey block is the range the author predicted (differences under %.1f points count as none, %.1f or more as large). A dot inside its block is a hit.</p>' % (rules["none_below"], rules["large_from"]))
    S.append('<p class="legend"><span class="lg"><svg width="34" height="12" aria-hidden="true"><line class="ci" x1="2" x2="32" y1="6" y2="6"/><circle class="dot" cx="17" cy="6" r="5"/></svg> observed difference, 95% interval</span><span class="lg"><svg width="26" height="14" aria-hidden="true"><rect class="zone" x="1" y="0" width="24" height="14" rx="3"/></svg> predicted range</span></p>')
    S.append('<div class="scroll"><div class="forestwrap">%s</div></div><div id="tip" class="tip" hidden></div></section>' % forest_svg(R))

    # ---- per-pair table
    S.append('<section><h2>Per-pair scores</h2><p class="prose">Composite = %d%% prediction + %d%% confounds + %d%% originality + %d%% comprehension. Prediction and comprehension come from the judges\' behavior. Confounds and originality come from blind model auditors and are opinions; treat them as provisional.</p>%s' % (
        tuple(round(100 * rules["weights"][k]) for k in ("prediction", "confounds", "originality", "comprehension")) + (prediction_rule_note(rules),)))
    S.append('<div class="scroll"><table class="data pairs"><thead><tr><th>Pair</th><th>Factor</th><th>Predicted, then observed</th><th class="n">A − B [95% interval]</th><th class="n">Prediction</th><th class="n">Confounds (0–3)</th><th class="n">Originality (0–3)</th><th class="n">Compre&shy;hension</th><th class="n">Composite</th></tr></thead><tbody>')
    order = ranked + [p for p in P if p["pair_type"] == "control_classic"] + [p for p in P if p["pair_type"] == "control_null"]
    last_type = None
    for p in order:
        if p["pair_type"] != last_type:
            name = {"authored": "Authored pairs, best composite first", "control_classic": "Classic controls", "control_null": "Null controls"}[p["pair_type"]]
            S.append('<tr class="grouprow"><th colspan="9">%s</th></tr>' % name)
            last_type = p["pair_type"]
        e, au, c = p["effect"], p.get("audit"), p["components"]
        S.append('<tr><td><a href="#%s" class="plain">%s</a>%s</td><td>%s</td><td>%s<br><span class="muted">%s</span></td><td class="n">%s [%s, %s]<br><span class="muted">%d of %d models</span></td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%.0f%%</td><td class="n strong">%s</td></tr>' % (
            esc(p["pair_id"]) if p in best + worst else "pairs", esc(pair_label(p)),
            ('<br><span class="flags">%s</span>' % esc("; ".join(p["flags"]))) if p["flags"] else "",
            esc(fac.get(p["factor_id"], "")) if p["factor_id"] != "null" else esc("null: " + (p.get("null_detail") or "")),
            esc(pred_text(p["prediction"])), esc(obs_text(p["observed"])), sgn(e["effect"]), sgn(e["ci_low"]), sgn(e["ci_high"]), e["groups_same_sign"], e["groups_total"],
            prediction_cell(p, rules),
            ("%d" % au["confound_severity"]) if au else "–", ("%d" % au["originality"]) if au else "–",
            100 * p["comprehension"]["accuracy"], ("%.0f" % p["composite"]) if p["composite"] is not None else "–"))
    S.append('</tbody></table></div><p class="note">Confounds run from 0 (none) to 3 (severe); the harsher middle grade of the four auditors is used. Originality runs from 0 (a re-skin of a known case) to 3 (fresh); the lower middle grade is used. “Models” counts the judge models whose own gap has the same sign as the overall gap. Control pairs were written by the builder and are scored the same way for comparison.</p></section>')

    # ---- authors
    S.append('<section><h2>Per-author summary</h2><p class="prose">Five pairs per author, one per factor. With five pairs each, differences between authors are descriptive only.</p><div class="scroll"><table class="data"><thead><tr><th>Author</th><th class="n">Mean composite</th><th class="n">Mean prediction score</th><th class="n">Direction right</th><th class="n">Size right</th><th class="n">Both right</th><th class="n">Mean |A − B|</th><th class="n">Confounds (0–3)</th><th class="n">Originality (0–3)</th><th class="n">Compre&shy;hension</th><th class="n">Words changed</th><th class="n">Shared setting</th></tr></thead><tbody>')
    for a in sorted(R["authors"], key=lambda a: TIER_ORDER.index(a["tier"]) if a["tier"] in TIER_ORDER else 9):
        old_ps = a.get("mean_prediction_score_classes_rule")
        ps_cell = "%.2f" % a["mean_prediction_score"] + (('<br><span class="muted">was %.2f</span>' % old_ps)
                                                         if rules.get("prediction_rule") == "distance" and old_ps is not None and abs(old_ps - a["mean_prediction_score"]) > 1e-9 else "")
        S.append('<tr><td class="nowrap">%s<br><span class="muted mono">%s</span></td><td class="n strong">%s</td><td class="n">%s</td><td class="n">%d / %d</td><td class="n">%d / %d</td><td class="n">%d / %d</td><td class="n">%.2f</td><td class="n">%s</td><td class="n">%s</td><td class="n">%.0f%%</td><td class="n">%.0f</td><td class="n">%d</td></tr>' % (
            esc(a["tier"]), esc(a["author_id"].split("/")[-1]), ("%.1f" % a["mean_composite"]) if a["mean_composite"] is not None else "–", ps_cell,
            a["direction_hits"], a["n_pairs"], a["size_hits"], a["n_pairs"], a["full_hits"], a["n_pairs"], a["mean_abs_effect"],
            ("%.2f" % a["mean_confound_severity"]) if a["mean_confound_severity"] is not None else "–",
            ("%.2f" % a["mean_originality"]) if a["mean_originality"] is not None else "–",
            100 * a["mean_comprehension"], a["mean_words_changed"], a.get("n_shared_setting", 0)))
    S.append("</tbody></table></div>")
    if comm.get("author_note"):
        S.append("".join('<p class="prose">%s</p>' % md_inline(x) for x in comm["author_note"]))
    S.append("</section>")

    # ---- proposed gate-based scoring
    gated = [p for p in authored if p.get("gated")]
    if gated:
        S.append('<section><h2>Proposed scoring for the next round</h2><p class="prose">The composite above mixes behavior with model opinion. This alternative scores behavior only (prediction and comprehension) and uses the audits as pass or fail gates: a pair fails if its confound grade is 2 or worse, if it is graded a re-skin, or if it shares a setting with another pair. It is shown beside the composite and replaces nothing. The shared-setting flags are the builder\'s own reading and no one has confirmed them.</p>')
        S.append('<div class="scroll"><table class="data"><thead><tr><th>Author</th><th class="n">Pairs passing both gates</th><th class="n">Mean behavior score of passing pairs</th><th>Pairs that fail, and why</th></tr></thead><tbody>')
        for a in sorted(R["authors"], key=lambda a: TIER_ORDER.index(a["tier"]) if a["tier"] in TIER_ORDER else 9):
            fails = ["%s (%s)" % (p["title"], ", ".join(p["gated"]["fails_on"])) for p in gated if p["author_tier"] == a["tier"] and not p["gated"]["passes"]]
            mb = a.get("gated_mean_behavior_of_passing")
            S.append('<tr><td>%s</td><td class="n">%d / %d</td><td class="n">%s</td><td class="wrap">%s</td></tr>' % (
                esc(a["tier"]), a.get("gated_passes", 0), a["n_pairs"], ("%.0f" % mb) if mb is not None else "–", esc("; ".join(fails)) or "none"))
        n_pass = sum(1 for p in gated if p["gated"]["passes"])
        S.append('</tbody></table></div><p class="note">%d of %d authored pairs pass both gates. Without the shared-setting rule, %d would.</p></section>' % (
            n_pass, len(gated), sum(1 for p in gated if p["gated"]["confound_gate"] and "re-skin" not in p["gated"]["fails_on"])))

    # ---- second judge panel from another vendor (only when the comparison files match this run)
    if vend:
        S.extend(vend)
        if comm.get("vendor_note"):
            S.append("".join('<p class="prose">%s</p>' % md_inline(x) for x in comm["vendor_note"]))
        S.append("</section>")

    # ---- persona judges (only when the comparison files match this run)
    if pers:
        S.extend(pers)
        if comm.get("persona_note"):
            S.append("".join('<p class="prose">%s</p>' % md_inline(x) for x in comm["persona_note"]))
        S.append("</section>")

    # ---- best / worst
    notes = comm.get("pairs", {})
    def rank_of(p):
        r = 1 + sum(1 for q in ranked if sc(q) > sc(p))
        tied = sum(1 for q in ranked if sc(q) == sc(p)) > 1
        return "%srank %d of %d" % ("tied at " if tied else "", r, len(ranked))
    tie_note = " Two pairs tie for third place, so four are shown." if len(best) == 4 else (" Ties at the cut are all shown." if len(best) > 3 else "")
    S.append('<section id="pairs"><h2>The three best pairs</h2><p class="prose">Best by composite score.%s Words that differ between the two versions are highlighted. Each card ends with what is wrong with the pair, including the good ones.</p>' % tie_note)
    for p in best:
        S.append(pair_card(p, R, "Best: " + rank_of(p), notes.get(p["pair_id"])))
    S.append('</section><section><h2>The three worst pairs</h2>')
    for p in worst:
        S.append(pair_card(p, R, "Worst: " + rank_of(p), notes.get(p["pair_id"])))
    S.append("</section>")

    # ---- controls
    S.append('<section><h2>Controls in detail</h2><h3>Classic pairs</h3><div class="scroll"><table class="data"><thead><tr><th>Control</th><th>Human reference result</th><th>Expected</th><th class="n">A − B [95% interval]</th><th>Panel</th></tr></thead><tbody>')
    for p in [p for p in P if p["pair_type"] == "control_classic"]:
        e = p["effect"]
        ok = p["observed"]["direction"] == p["prediction"]["direction"]
        ref = p.get("reference") or {}
        ver = (ref.get("verification") or {}).get("status", "")
        ver_chip = {"verified": chip("✓ checked against the paper", "good"), "partly verified": chip("! partly checked against the papers", "warn"),
                    "not verified": chip("✕ not checked against the paper", "bad")}.get(ver, "")
        S.append('<tr><td>%s<br><span class="muted">%s</span></td><td class="wrap">%s <span class="muted">%s</span><br>%s</td><td>%s</td><td class="n">%s [%s, %s]</td><td>%s</td></tr>' % (
            esc(p["title"]), esc(fac.get(p["factor_id"], "")), esc(ref.get("human_result", "")), esc(ref.get("source", "")), ver_chip, esc(pred_text(p["prediction"])),
            sgn(e["effect"]), sgn(e["ci_low"]), sgn(e["ci_high"]), chip("✓ reproduced", "good") if ok else chip("✕ " + obs_text(p["observed"]), "bad")))
    S.append('</tbody></table></div><h3>Null pairs</h3><div class="scroll"><table class="data"><thead><tr><th>Control</th><th>Detail changed</th><th class="n">Mean A</th><th class="n">Mean B</th><th class="n">A − B [95% interval]</th><th>Panel</th></tr></thead><tbody>')
    for p in [p for p in P if p["pair_type"] == "control_null"]:
        e = p["effect"]
        fp = p["observed"]["direction"] in ("A_higher", "B_higher")
        S.append('<tr><td>%s</td><td>%s</td><td class="n">%.2f</td><td class="n">%.2f</td><td class="n">%s [%s, %s]</td><td>%s</td></tr>' % (
            esc(p["title"]), esc(p.get("null_detail") or ""), e["mean_a"], e["mean_b"], sgn(e["effect"]), sgn(e["ci_low"]), sgn(e["ci_high"]),
            chip("✕ false gap", "bad") if fp else (chip("! interval excludes 0", "warn") if p["observed"]["ci_excludes_zero"] else chip("✓ no gap", "good"))))
    S.append("</tbody></table></div>")
    if panel["auditors"]:
        S.append('<h3>Were the auditors any good?</h3><p class="prose">Auditors saw both versions of every pair, with authors hidden. Three extra pairs carried a planted confound that their stated difference did not admit; the five classic pairs should be recognised as known cases; the five null pairs differ in one trivial detail and should be rated clean.</p><div class="scroll"><table class="data"><thead><tr><th>Auditor</th><th class="n">Planted confounds rated moderate or worse</th><th class="n">Planted confounds named</th><th class="n">Classics recognised</th><th class="n">Null pairs wrongly rated confounded</th><th class="n">Mean severity, own pairs</th><th class="n">Mean severity, others\' pairs</th><th class="n">Mean originality, own</th><th class="n">Mean originality, others\'</th></tr></thead><tbody>')
        f2 = lambda x: "–" if x is None else "%.2f" % x
        for a in sorted(panel["auditors"], key=lambda g: TIER_ORDER.index(short_group(g)) if short_group(g) in TIER_ORDER else 9):
            c = panel["auditors"][a]
            S.append('<tr><td>%s</td><td class="n">%d / %d</td><td class="n">%d / %d</td><td class="n">%d / %d</td><td class="n">%d / %d</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td></tr>' % (
                esc(short_group(a)), c["planted_confounds_rated_2_plus"], c["planted_total"], c["planted_confounds_named"], c["planted_total"],
                c["classics_flagged_as_known"], c["classics_total"], c["null_pairs_rated_2_plus"], c["nulls_total"],
                f2(c["own_tier_mean_severity"]), f2(c["other_tier_mean_severity"]), f2(c["own_tier_mean_originality"]), f2(c["other_tier_mean_originality"])))
        S.append("</tbody></table></div>")
        ag = panel.get("auditor_agreement") or {}
        if ag.get("confound_severity"):
            c, o = ag["confound_severity"], ag["originality"]
            S.append('<p class="prose">On the %d authored pairs, two auditors gave the same confound grade %.1f%% of the time and the same originality grade %.1f%% of the time. On %.0f%% of pairs the auditors were two or more grades apart on confounds.</p>' % (
                c["n_pairs"], 100 * c["exact_agreement"], 100 * o["exact_agreement"], 100 * c["share_of_pairs_two_or_more_apart"]))
        ba = panel.get("auditor_by_author") or {}
        if ba:
            tiers = [t for t in TIER_ORDER if any(t in ba[a] for a in ba)]
            S.append('<div class="scroll"><table class="data"><thead><tr><th>Mean confound severity given by</th>%s</tr></thead><tbody>' % "".join('<th class="n">to the %s author</th>' % esc(t) for t in tiers))
            for a in sorted(ba, key=lambda g: TIER_ORDER.index(short_group(g)) if short_group(g) in TIER_ORDER else 9):
                S.append("<tr><td>%s auditor</td>%s</tr>" % (esc(short_group(a)), "".join(
                    '<td class="n%s">%s</td>' % (" strong" if t == short_group(a) else "", ("%.1f" % ba[a][t]["confound_severity"]) if t in ba[a] else "–") for t in tiers)))
            S.append('</tbody></table></div><p class="note">Bold marks an auditor grading pairs written by its own model. Auditors did not know who wrote what.</p>')
    if comm.get("controls_note"):
        S.append("".join('<p class="prose">%s</p>' % md_inline(x) for x in comm["controls_note"]))
    S.append("</section>")

    # ---- panel diagnostics
    S.append('<section><h2>How each judge model used the scale</h2><div class="scroll"><table class="data"><thead><tr><th>Judge model</th><th class="n">Judges</th><th class="n">Ratings</th><th class="n">Mean rating</th><th class="n">Ratings of 1 or 7</th><th class="n">Scenarios where all repeats agreed</th><th class="n">Comprehension</th><th class="n">Mean |A − B|, authored</th><th class="n">Mean |A − B|, nulls</th><th class="n">Nulls at 0.5 or more on this model alone</th></tr></thead><tbody>')
    for g in sorted(panel["by_group"], key=lambda g: TIER_ORDER.index(short_group(g)) if short_group(g) in TIER_ORDER else 9):
        d = panel["by_group"][g]
        S.append('<tr><td class="nowrap">%s<br><span class="muted mono">%s</span></td><td class="n">%d</td><td class="n">%d</td><td class="n">%.2f</td><td class="n">%.0f%%</td><td class="n">%s</td><td class="n">%.1f%%</td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td></tr>' % (
            esc(short_group(g)), esc(g.split("/")[-1]), d["n_judges"], d["n_judgments"], d["mean_rating"], 100 * d["share_extreme"],
            ("%.0f%%" % (100 * d["share_cells_zero_variance"])) if d["share_cells_zero_variance"] is not None else "–",
            100 * d["comprehension_accuracy"], ("%.2f" % d["mean_abs_effect_authored"]) if d["mean_abs_effect_authored"] is not None else "–",
            ("%.2f" % d["mean_abs_effect_nulls"]) if d["mean_abs_effect_nulls"] is not None else "–",
            ("%d of %d" % (d["nulls_half_point_or_more"], panel["nulls_total"])) if "nulls_half_point_or_more" in d else "–"))
    S.append("</tbody></table></div>")
    ot = panel["own_tier"]
    extra = []
    if ot["mean_own"] is not None:
        ci = ot.get("mean_difference_ci")
        extra.append("Judges from an author's own model produced a gap of %s points in the predicted direction on that author's pairs, against %s from the other three models; the own-model gap was the larger one on %d of %d pairs%s." % (
            sgn(ot["mean_own"]), sgn(ot["mean_others"]), ot.get("n_own_larger", 0), len(ot["pairs"]),
            (" (difference %s, 95%% interval %s to %s)" % (sgn(ot["mean_own"] - ot["mean_others"]), sgn(ci[0]), sgn(ci[1]))) if ci else ""))
    ml = panel.get("model_level_interval")
    if ml is not None:
        extra.append("A wider interval that also resamples the judge models would withdraw %d confirmed gap%s and leaves %d null pair%s with an interval that excludes zero." % (
            len(ml["gaps_no_longer_confirmed"]), "" if len(ml["gaps_no_longer_confirmed"]) == 1 else "s", ml["nulls_excluding_zero"], "" if ml["nulls_excluding_zero"] == 1 else "s"))
    if panel["position_effect_r"] is not None:
        extra.append("Position in the batch correlates %s with how far a rating sits from that scenario's average." % sgn(panel["position_effect_r"], 3))
    S.append('<p class="prose">%s</p>' % " ".join(extra))
    if comm.get("diagnostics_note"):
        S.append("".join('<p class="prose">%s</p>' % md_inline(x) for x in comm["diagnostics_note"]))
    S.append("</section>")

    # ---- methods + files
    if methods_html:
        S.append('<section class="methods" id="methods"><p class="eyebrow">Methods note</p>%s</section>' % methods_html)
    S.append('<section><h2>Files and how to rerun</h2><ul class="files"><li><code>vignettes.json</code>: all pairs, questions, predictions, authors and the control references.</li><li><code>judgments.csv</code>: one row per judge and scenario, with judge type, vendor, model and group, so other vendors\' models and human judges can be appended.</li><li><code>audits.csv</code>: one row per auditor and pair.</li>%s%s<li><code>score.py</code>: run <code>python3 score.py</code> to recompute every number and rebuild this page from the files above.</li><li><code>METHODS.md</code>, <code>docs/prior-art.md</code> and <code>docs/control-references.md</code>: the methods note, the prior-art check, and the check of the control references against their sources.</li></ul><p class="note">%s judgments · %d judges · %d judge models · %d bootstrap resamples · seed %d.%s</p></section>' % (
        ('<li><code>pipeline/compare_vendor_panels.py</code>: scores the second panel (run <code>%s</code> in <code>judgments.csv</code>) and rebuilds the side-by-side section; details in <code>reports/Pilot rescored with Gemini.md</code>.</li>' % esc(vsumm.get("other_run", "gemini"))) if vend else "",
        ('<li><code>pipeline/compare_persona_panel.py</code>: scores the persona panel (run <code>%s</code> in <code>judgments.csv</code>) and rebuilds its section; details in <code>reports/Pilot rescored with persona judges.md</code>.</li>' % esc(psumm.get("new_run", "persona"))) if pers else "",
        format(data["n_judgments"], ","), data["n_judges"], n_models, R["bootstrap"]["resamples"], R["bootstrap"]["seed"],
        (" Data problems: " + esc("; ".join(data["problems"]))) if data["problems"] else ""))

    body = "\n".join(S)
    frag = HEAD + STYLE + '<main class="page">\n' + body + "\n</main>\n" + SCRIPT
    os.makedirs(os.path.join(root, "out"), exist_ok=True)
    open(os.path.join(root, "out", "results_page.html"), "w", encoding="utf-8").write(frag)
    full = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + HEAD + STYLE + '</head>\n<body>\n<main class="page">\n' + body + "\n</main>\n" + SCRIPT + "</body>\n</html>\n"
    open(os.path.join(root, "results.html"), "w", encoding="utf-8").write(full)
    print("wrote", os.path.join(root, "results.html"), "(%d KB)" % (len(full) // 1024))


HEAD = '''<title>Thought-experiment authoring pilot</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:ital,wght@0,400;0,500;1,400&display=swap">
'''

STYLE = '''<style>
/* Layout: one reading column of analysis in sans; the stimuli themselves are set in serif, like a printed questionnaire. */
:root {
  --bg: #f5f6f8; --surface: #fdfdfe; --ink: #14171c; --ink-2: #474e59; --muted: #747c88;
  --hair: #e1e4ea; --base: #c2c8d1; --band: #e3e7ee; --mark: #fff1c2;
  --series-a: #2a78d6; --series-b: #eb6834;
  --good: #0a7a0a; --good-bg: #e4f4e4; --warn: #8a5a00; --warn-bg: #fdf0cf; --bad: #b3261e; --bad-bg: #fbe6e4;
  --sans: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --serif: "IBM Plex Serif", Georgia, "Times New Roman", serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #0e1013; --surface: #171a1f; --ink: #eef0f3; --ink-2: #c1c6ce; --muted: #8f96a1;
  --hair: #292d34; --base: #3b4049; --band: #2a2f38; --mark: #4a3d12;
  --series-a: #3987e5; --series-b: #d95926;
  --good: #4cc04c; --good-bg: #14301a; --warn: #f0b93a; --warn-bg: #3a2e0f; --bad: #f08a80; --bad-bg: #3d1a17; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #0e1013; --surface: #171a1f; --ink: #eef0f3; --ink-2: #c1c6ce; --muted: #8f96a1;
  --hair: #292d34; --base: #3b4049; --band: #2a2f38; --mark: #4a3d12;
  --series-a: #3987e5; --series-b: #d95926;
  --good: #4cc04c; --good-bg: #14301a; --warn: #f0b93a; --warn-bg: #3a2e0f; --bad: #f08a80; --bad-bg: #3d1a17; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 15px; line-height: 1.55; }
.page { max-width: 1080px; margin: 0 auto; padding-block: 36px 72px; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); display: flex; flex-direction: column; gap: 44px; }
section, header.top { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
h1 { font-size: 34px; line-height: 1.15; font-weight: 600; letter-spacing: -0.01em; margin: 0; text-wrap: balance; }
h2 { font-size: 22px; line-height: 1.25; font-weight: 600; margin: 0; text-wrap: balance; }
h3 { font-size: 17px; font-weight: 600; margin: 8px 0 0; text-wrap: balance; }
h4 { font-size: 13px; font-weight: 600; margin: 0; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-2); }
h5 { font-size: 14px; font-weight: 600; margin: 0; }
p { margin: 0; }
a { color: var(--series-a); }
a.plain { color: inherit; text-decoration-color: var(--base); }
a:focus-visible, .row:focus-visible, summary:focus-visible { outline: 2px solid var(--series-a); outline-offset: 2px; }
.eyebrow { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); font-weight: 500; }
.lede { font-size: 17px; max-width: 68ch; color: var(--ink-2); }
.prose, .findings { max-width: 72ch; color: var(--ink-2); }
.findings { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; }
.note { font-size: 13px; color: var(--muted); max-width: 80ch; }
.muted { color: var(--muted); } .mono { font-family: var(--mono); font-size: 12px; }
code { font-family: var(--mono); font-size: 0.9em; background: var(--band); padding: 1px 5px; border-radius: 4px; }
.caveat { border: 1px solid var(--base); border-left: 4px solid var(--warn); background: var(--surface); padding: 14px 16px; border-radius: 6px; max-width: 80ch; color: var(--ink-2); }
.caveat strong { color: var(--ink); }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
.tile { background: var(--surface); border: 1px solid var(--hair); border-radius: 8px; padding: 14px 16px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.tl { font-size: 13px; color: var(--ink-2); } .tn { font-size: 12px; color: var(--muted); }
.tv { font-size: 32px; font-weight: 600; line-height: 1.2; } .tv span { font-size: 15px; font-weight: 400; color: var(--muted); }
.scroll { overflow-x: auto; background: var(--surface); border: 1px solid var(--hair); border-radius: 8px; }
.forestwrap { min-width: 860px; padding: 12px 14px 6px; }
svg text { font-family: var(--sans); fill: var(--ink-2); }
.forest .grid, .strip .grid { stroke: var(--hair); stroke-width: 1; }
.forest .zero { stroke: var(--base); stroke-width: 1.5; }
.forest .tick, .strip .tick { font-size: 11px; fill: var(--muted); font-variant-numeric: tabular-nums; }
.forest .axis { font-size: 11.5px; fill: var(--muted); }
.forest .colhead { font-size: 11px; fill: var(--muted); }
.forest .grp { font-size: 12.5px; font-weight: 600; fill: var(--ink); }
.forest .lab { font-size: 12.5px; fill: var(--ink-2); }
.forest .num { font-size: 12px; font-variant-numeric: tabular-nums; fill: var(--ink-2); }
.forest .verdict { fill: var(--muted); }
.zone { fill: var(--band); }
.ci { stroke: var(--series-a); stroke-width: 2; stroke-linecap: round; }
.dot { fill: var(--series-a); stroke: var(--surface); stroke-width: 2; }
.dot.b { fill: var(--series-b); }
.forest .hit { fill: transparent; }
.forest .row:hover .hit, .forest .row:focus .hit { fill: var(--band); opacity: 0.45; }
.forest .row { outline: none; }
.legend { display: flex; flex-wrap: wrap; gap: 18px; font-size: 13px; color: var(--ink-2); }
.lg { display: inline-flex; align-items: center; gap: 6px; }
.tip { position: fixed; z-index: 20; background: var(--ink); color: var(--bg); font-size: 12.5px; line-height: 1.45; padding: 9px 11px; border-radius: 6px; max-width: 300px; pointer-events: none; }
.tip b { font-weight: 600; }
table.data { border-collapse: collapse; width: 100%; font-size: 13px; }
table.data th, table.data td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--hair); vertical-align: top; }
table.data thead th { font-size: 12px; font-weight: 600; color: var(--ink-2); border-bottom: 1px solid var(--base); white-space: normal; min-width: 64px; }
table.data td.n, table.data th.n { text-align: right; font-variant-numeric: tabular-nums; }
table.data td.n { white-space: nowrap; }
table.data td.wrap { min-width: 280px; max-width: 420px; }
table.pairs th:first-child, table.pairs td:first-child { min-width: 210px; }
table.pairs td:nth-child(2) { min-width: 120px; } table.pairs td:nth-child(3) { min-width: 130px; }
table.data td.nowrap { white-space: nowrap; }
table.data td.strong { font-weight: 600; color: var(--ink); }
table.data tr.grouprow th { background: var(--bg); font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 600; }
table.data tbody tr:last-child td { border-bottom: 0; }
table.data tr.differ td { background: color-mix(in srgb, var(--warn-bg) 55%, transparent); }
.flags { font-size: 11.5px; color: var(--warn); }
.chip { display: inline-block; font-size: 11.5px; padding: 2px 8px; border-radius: 999px; background: var(--band); color: var(--ink-2); white-space: nowrap; }
.chip.good { background: var(--good-bg); color: var(--good); } .chip.warn { background: var(--warn-bg); color: var(--warn); white-space: normal; } .chip.bad { background: var(--bad-bg); color: var(--bad); white-space: normal; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.card { background: var(--surface); border: 1px solid var(--hair); border-radius: 10px; padding: 20px; display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.card > header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.card h3 { margin: 2px 0; font-size: 19px; } .card .sub { font-size: 13px; color: var(--muted); }
.score { text-align: right; white-space: nowrap; } .score .big { font-size: 30px; font-weight: 600; } .score .of { font-size: 13px; color: var(--muted); margin-left: 3px; }
.versions { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }
.versions > div { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.wc { font-weight: 400; text-transform: none; letter-spacing: 0; color: var(--muted); margin-left: 6px; }
.vig { font-family: var(--serif); font-size: 15.5px; line-height: 1.6; color: var(--ink); }
mark.chg { background: var(--mark); color: inherit; padding: 1px 2px; border-radius: 3px; }
.q { font-size: 14px; color: var(--ink-2); max-width: 90ch; }
.result { display: grid; grid-template-columns: minmax(0, 1fr) minmax(260px, 420px); gap: 20px; align-items: start; border-top: 1px solid var(--hair); padding-top: 14px; }
@media (max-width: 760px) { .result { grid-template-columns: minmax(0, 1fr); } .card > header { flex-direction: column; } .score { text-align: left; } h1 { font-size: 28px; } }
.rtext { display: flex; flex-direction: column; gap: 8px; font-size: 14px; color: var(--ink-2); min-width: 0; }
.comp { font-size: 12.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
.stripwrap { margin: 0; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.stripwrap figcaption { font-size: 12px; color: var(--muted); }
.key.a { color: var(--series-a); } .key.b { color: var(--series-b); }
.strip { width: 100%; height: auto; max-width: 460px; }
.strip .lab { font-size: 12px; fill: var(--ink-2); } .strip .vtag { font-size: 10.5px; fill: var(--muted); }
details { font-size: 13.5px; color: var(--ink-2); } details summary { cursor: pointer; font-weight: 500; color: var(--ink); }
details ul { margin: 6px 0 10px; padding-left: 20px; } details p { margin-top: 8px; }
.diagnosis { background: var(--bg); border-radius: 8px; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
.diagnosis p { max-width: 80ch; color: var(--ink); font-size: 14.5px; }
.methods { background: var(--surface); border: 1px solid var(--hair); border-radius: 10px; padding: 24px; gap: 10px; }
.methods h2 { font-size: 22px; } .methods h3 { font-size: 16px; margin-top: 10px; } .methods p, .methods li { max-width: 78ch; color: var(--ink-2); font-size: 14.5px; }
.methods ul, .methods ol { margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 5px; }
.files { margin: 0; padding-left: 20px; color: var(--ink-2); display: flex; flex-direction: column; gap: 4px; max-width: 80ch; }
@media (prefers-reduced-motion: no-preference) { .forest .hit { transition: opacity .12s; } }
</style>
'''

SCRIPT = '''<script>
(function () {
  var tip = document.getElementById('tip');
  if (!tip) return;
  function show(el, x, y) {
    var d; try { d = JSON.parse(el.getAttribute('data-tip')); } catch (e) { return; }
    tip.innerHTML = '';
    var rows = [['', d.t, true], ['Predicted', d.p], ['Observed', d.o], ['A minus B', d.e], ['Mean A / B', d.a + ' / ' + d.b], ['Models agreeing', d.g], ['Verdict', d.v]];
    rows.forEach(function (r) {
      var div = document.createElement('div');
      if (r[2]) { var b = document.createElement('b'); b.textContent = r[1]; div.appendChild(b); }
      else { div.textContent = r[0] + ': ' + r[1]; }
      tip.appendChild(div);
    });
    tip.hidden = false;
    var w = tip.offsetWidth, h = tip.offsetHeight;
    var left = Math.min(Math.max(8, x + 14), window.innerWidth - w - 8);
    var top = y + 16 + h > window.innerHeight ? y - h - 10 : y + 16;
    tip.style.left = left + 'px'; tip.style.top = Math.max(8, top) + 'px';
  }
  document.querySelectorAll('.forest .row').forEach(function (el) {
    el.addEventListener('mousemove', function (ev) { show(el, ev.clientX, ev.clientY); });
    el.addEventListener('mouseleave', function () { tip.hidden = true; });
    el.addEventListener('focus', function () { var r = el.getBoundingClientRect(); show(el, r.left + r.width / 2, r.top + r.height); });
    el.addEventListener('blur', function () { tip.hidden = true; });
  });
})();
</script>
'''

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    build(json.load(open(os.path.join(here, "out", "results.json"), encoding="utf-8")), here)
