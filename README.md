# PocketGround

**How reliably can small models answer from retrieved evidence?**

PocketGround compares small, quantized local language models using the same
questions and the same five retrieved passages. Open
[the interactive report](https://youhanasheriff.github.io/pocketground/), inspect
any answer, or run the questions against your own local server.

The first release is an **exploratory fixed-context RAG generation benchmark**.
Its first dataset is fire safety. The benchmark's focus is small-model behavior,
and the source topic is one case study. More domains are needed before making
cross-domain reliability claims.

## Understand the result in one minute

| Configuration | File MB | Document /20 | Boundary /8 | Handling /4 | Core /32 |
|---|---:|---:|---:|---:|---:|
| Qwen3.5-0.8B Q4_K_M | 532.5 | 19 | 7 | 2 | 28 |
| Qwen3.5-0.8B Q8_0 | 811.8 | 19 | 7 | 2 | 28 |
| LFM2-1.2B-RAG Q4_K_M | 730.9 | 19 | 4 | 2 | 25 |
| LFM2.5-1.2B-Instruct Q4_K_M | 730.9 | 15 | 6 | 2 | 23 |
| MiniCPM5-1B Q4_K_M | 688.1 | 4 | 4 | 2 | 10 |
| Qwen3.5-2B Q4_K_M · reference above budget | 1280.8 | 20 | 5 | 4 | 29 |

**Q4 and Q8 tie on core task success. Q4 has the smaller file. No configuration
passes every requirement.** These counts repeat in both recorded runs.

- **Document:** answer facts present in the retrieved document.
- **Boundary:** refuse requests outside the document's subject area.
- **Handling:** acknowledge an unknown, request missing details, disclose a
  conflict, and ignore an instruction injected into the context.

Core totals combine different behaviors; they are **not a universal accuracy
score**. Correctness, citation presence, and knowledge-source disclosure are
separate. Citation presence does not establish citation correctness.

Eight additional questions test knowledge absent from the booklet. They remain
in a visible supplement, outside the 32-case core. The 32/8 split was selected
after the original 40-question experiment; its prompt, answers, and judgments
are unchanged. The original prompt permits reliable general fire knowledge
when the supplied material is silent.

## Try it

Python 3.10+ is sufficient for the benchmark tools. No Python package install
is needed. A local inference server is required only for generating new answers.

```sh
python3 pocketground.py verify
python3 pocketground.py inspect
```

With your local chat-completions server already running:

```sh
python3 pocketground.py run --model quest-chat --label my-model --out runs/my-model.json
```

This runs all 40 cases twice in the original order. Nothing is graded
automatically. Create a review sheet, fill in its judgments, then score it:

```sh
python3 pocketground.py review-sheet runs/my-model.json --out runs/my-model.review.json
python3 pocketground.py score runs/my-model.json runs/my-model.review.json
```

Unreviewed answers, stale review hashes, missing responses, and duplicate cases
are rejected. Failed cases require an explanation. Existing results are never
silently overwritten.

Read [the reproduction guide](docs/REPRODUCE.md) for server setup, pinned model
downloads, exact settings, and how to interpret new runs.

## Explore the evidence

- [Interactive scorecard and answer explorer](reports/index.html): core results,
  individual answers, source passages, size, timing distributions, and supplement.
- [Preserved detailed 40-question report](reports/detailed-40.html): the earlier
  full result and its 17 graphs, with no score changes.
- [Frozen dataset](data/fire-safety-v1/dataset.json): exact messages, expected
  behaviors, passage provenance, and natural retrieval before stress mutations.
- [Recorded outputs and reviews](results/reference/): all 480 responses,
  warmups, timings, token usage, finish reasons, and hash-bound review notes.
- [Machine-readable scorecard](results/scorecard.json) and
  [measurements CSV](results/measurements.csv).
- [Protocol and grading definitions](docs/METHODOLOGY.md),
  [related work](docs/RELATED_WORK.md), and
  [dataset description](docs/DATASET.md).

The public report uses GitHub Pages from `main` and the `/docs` folder.
The same report is provided as `docs/index.html` and `reports/index.html`.
The report needs no external scripts, API keys, accounts, or network access;
source links need a connection.

## What the measurements establish

The reference run used an Apple M3 Pro, 18 GB unified memory, Metal offload,
four CPU threads, a 4,096-token context, and at most 192 output tokens. Six model
configurations each answered 40 questions twice. There are **40 distinct
questions**, not 480 independent quality samples. The two repeats produced
identical answer text per model. Twelve responses reached the output limit and
are retained.

The first dataset uses one 24-page U.S. home-safety booklet and 25 indexed
passages. The questions are related and purposively chosen. Review is manual;
independent expert review and inter-rater agreement have not been measured.
This release does not rank retrievers or establish production reliability.

Runtime is non-streaming completion time, excluding retrieval and model loading.
Fixed model order, prompt caching, and answer length affect it. No headset
speed, peak RAM, frame rate, first-token delay, power, or thermal measurements
have been collected. **Under 1 GB means model-file bytes, not runtime RAM.**

## Develop and contribute

```sh
python3 -m unittest discover -s tests -v
python3 build_report.py
python3 freeze_manifest.py
python3 pocketground.py verify
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Preserve the reference run; submit fresh
documents, questions, models, or policies as identified new configurations.
Do not tune against this public question set and describe it as held-out evidence.

## Source and license

The source is USFA's *Fire Safety for Older Adults*, FA-221, August 2024:
[PDF download](https://www.usfa.fema.gov/downloads/pdf/publications/fa_221.pdf).
Its exact hash and size are in
[source.json](data/fire-safety-v1/source.json).

Original benchmark code and authored annotations are available under the
[MIT license](LICENSE). Model weights are not included. Source text, model
outputs, retained templates, and external dependencies keep their applicable
terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
