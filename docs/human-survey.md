# Human survey design and analysis plan

Prepared on 15 November 2026. No person has taken it yet. The project is paused until participants are found.

## What it is for

One human run on the existing 30 pairs, to find out two things the model panel cannot tell us:

1. Do the authored pairs split **people's** judgments the way their authors predicted?
2. How far can the cheap model panel be trusted as a stand-in for people?

## What a participant sees

- A short introduction and one consent tick box. Adults only; a note that some scenarios describe accidents, injuries or deaths.
- Two optional questions (philosophy background, English reading).
- Up to 30 scenarios, one per screen, in random order. Each has the same two questions the model judges answered: a 1 to 7 judgment and a three-option factual question. No going back.
- They can stop at any point; what they have answered still counts.
- One optional closing question (did any scenario seem familiar), then a **completion code** and a short explanation of what the study was for.

Each participant sees one version of every pair. The page contains no pair names, authors, factors, predictions or answer keys.

Time: about 20 minutes for all 30.

## How answers reach you

Nothing is sent automatically. The participant copies the completion code (text starting `TE1-`, about 200 characters) and sends it to you by whatever channel you used to invite them.

This is deliberate. The publishing platform's data store accepts writes only from the owner and members of the owner's own workspace, so it cannot collect answers from outside volunteers. The code works for anyone who can open the page.

The code holds the answers, time per scenario, the three optional background answers and a random participant code. It holds no name, email, device or account information. The channel a code arrives by does tell you who sent it, so keep the codes in a file without names if you want the answers unlinked from people.

## Form assignment

Participants are assigned to 20 complementary forms in rotation. The deployment
files and scoring key are outside this model-panel archive.

## How many people

| Complete responses | Ratings per version of each pair | What it supports |
|---|---|---|
| 16 | 8 | The minimum the analysis accepts; direction only, wide intervals |
| 40 | 20 | The same depth as the model panel |
| 80 | 40 | The target named in the methods note |

These figures assume forms are handed out in order. People who stop early count for the scenarios they answered.

## When codes come back

When the study runs, the response importer requires the separate survey manifest.
The planned workflow reads one completed code per line and then runs these commands:

```bash
python3 pipeline/ingest_survey.py codes.txt
```

```bash
python3 compare_panels.py
```

```bash
python3 score.py --run human-1 --out out/human-1 --no-report
```

The first adds rows to `judgments.csv` with `judge_type` "human" and writes `participants.csv`. A code that was cut or altered in copying fails its checksum and is reported, not ingested. The second writes `out/panel_comparison.csv` and prints the summary. The third scores the human panel alone with the same rules as the model panel.

The whole path was dry-run on invented participants in a scratch copy, which was then deleted. No invented data is in the project.

## Analysis plan, fixed before any human data

- **Same rules as the model panel.** A gap counts if it is at least 0.5 points and its 95% bootstrap interval excludes zero. Size bins are unchanged for this run.
- **Exclusions.** A participant is dropped if they answered at least five scenarios and got fewer than 80% of the factual questions right, or if their median time per scenario was under eight seconds. Results are also reported without exclusions.
- **Minimum data.** A pair is reported only with at least 8 human ratings per version.
- **Primary results.**
  1. Authored pairs whose predicted direction holds in people, overall and per author.
  2. Classic controls showing the expected direction in people; null controls showing a gap in people.
  3. Agreement between the panels: pairs on which both give the same verdict, the correlation of gaps across pairs, and the model gap per point of human gap.
- **Proposed bar for using the model panel alone afterwards** (yours to confirm before the data comes in): the panels give the same verdict on at least 24 of 30 pairs, the rank correlation of gaps is at least 0.7, and no null control shows a gap in people that the model panel missed.
- **After this run, not before:** re-set the size bins on the human data, and decide on harder factors.

## Things only you can decide or do

- **Ethics.** The survey collects no identifying information, is voluntary, is limited to adults, warns about content and explains itself at the end. Whether that is enough depends on where you work and who you recruit. If your institution requires review for surveys of people, get it before recruiting.
- **Recruiting.** Volunteers who know you, or who have studied philosophy, are not a cross-section of readers. The background questions let the analysis check for that, not remove it.

## Known limits of this survey

- Nothing stops one person taking it twice; each attempt gets a new random code.
- The page's source contains both versions of every scenario. A participant who goes looking can find them.
- People judge 30 scenarios in one sitting, several on the same theme, as the model judges did.
- Answers are tied to a specific set of scenarios and its manifest. A new survey build
requires its own manifest and codes.
