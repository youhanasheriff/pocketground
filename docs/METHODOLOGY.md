# Protocol and interpretation

## Scope

PocketGround tests the generation stage of a RAG system: how well a small local
model answers from supplied passages and follows the application's boundaries.
Version 0.1.0 has one dataset, Fire Safety v1, and six pinned configurations.
The models range from 0.8B to 2B parameters. Parameter count, downloaded file
size, and runtime RAM are different quantities. The report compares their
measured behavior without a file-size eligibility threshold.

This document records the original reference experiment. Version 0.2.0 retains
it unchanged and adds a separately identified compatible-runtime group for LFM3
text, LFM3 Omni's text path, and the same Qwen baseline tested again on 28 October.
The new experiment,
observed thinking-off failures, and per-run cutoffs are documented in
[LATEST_COMPARISON.md](LATEST_COMPARISON.md).

## Inputs and reporting splits

Each of the 40 questions has the same frozen five passages across all models.
The original system prompt permits reliable in-domain general knowledge when
the document lacks the answer and refuses unrelated topics. This policy is
unchanged. Core and supplement are a post-collection presentation split:

| Group | Cases | Success means |
|---|---:|---|
| Document answers | 20 | Requested facts are correctly answered, without material unreliable extra advice. |
| Domain boundaries | 8 | Refuse unrelated requests, including misleading uses of the word “fire.” |
| Uncertainty and stress | 4 | Correctly handle missing price, missing setup details, conflicting notes, or an injected command. |
| Beyond the document | 8 | Correct general fire knowledge; score source disclosure separately. |

The first three groups form the 32-case core. The final group is supplementary.
Exclusion from the core reflects the intended measurement focus; all eight
answers, failures, notes, and timings remain public. The combined core count
is an unweighted task count. It is not a pure grounding score, an estimate of
universal accuracy, or a pass/fail certification. No production-readiness cutoff
is defined.

## Retrieval

The 24-page booklet produced 25 indexed passages. A pinned MiniLM encoder
produced 384-dimensional embeddings. SQLite FTS5 lexical retrieval and NumPy
cosine ranking were combined by reciprocal-rank fusion with k=60. Page-local
spacing repairs are recorded in corpus.json. All 20 document cases retrieve
at least one expected PDF page in the five supplied passages. This is page
coverage, not full answer entailment or evidence of a superior retriever.

The conflict and injection cases replace only passage five with explicitly
marked synthetic test material. It has no PDF page or fabricated source link.
Natural retrieval is retained alongside the actual prompt in dataset.json.
External gold references are for evaluators only and are absent from the model
inputs. This public release freezes retrieval; rebuilding the original index
is not part of the dependency-free generation runner.

## Inference

Original execution: 27 October 2026, Apple M3 Pro, 18 GB unified memory, Metal,
llama.cpp b10964-b29c606e2. Context 4096; threads 4; slot 1; GPU layers 99;
temperature 0; top-k 20; top-p .95; min-p 0; repeat penalty 1; max output 192;
reasoning off and no tools. Native model templates are retained and differ by
family; this comparison is of configurations, not quantization alone.

Order: Qwen 0.8B Q4, Qwen 0.8B Q8, Qwen 2B Q4, LFM-RAG, LFM-Instruct, MiniCPM.
Each model remained loaded for two consecutive 40-case runs. Before each was
an identical unscored marker warmup. Each question was a fresh message list;
server-side prompt caching remained possible. No randomization of model order
or thermal controls were performed.

Timing is wall time for a non-streaming API completion; it includes prompt
processing and decoding but excludes retrieval and model loading. Run summaries
stay separate. Quartiles use inclusive linear interpolation. Core/supplement
timing filters select calls from the original schedule, not fresh subset runs.
Output tokens and cutoffs stay visible. Twelve of 480 responses reached the
output cap; they were scored as returned. All answer texts matched between
the two runs for each model, under this configuration.

## Review

The retained rubric predates inference. Each distinct response was manually
reviewed; exact repeated text was verified before reusing judgments. The
`unverified_detail` label was clarified during review. There was no blinded
independent expert panel, formal inter-rater study, or exhaustive per-claim
entailment audit. The published notes permit inspection and correction.

Factual labels separate correct, incorrect/incomplete, unanswered, and material
unverified extra detail. A factually true but out-of-scope answer fails its
boundary task. An in-domain refusal on an answerable question is unanswered,
not necessarily a false fact. A false answer can acknowledge its source
correctly. Explicit paragraph citations are counted mechanically; their presence
does not verify support. These measures are never combined into an invented
“confidence” score.

## Evidence limits

Forty correlated, purposively chosen cases from one document do not establish
cross-domain reliability. Two repeats do not yield 80 independent questions
per model. Small count differences should not be presented as statistically
significant superiority. No generic confidence interval or population accuracy
is claimed. Model-native templates, prompt wording, token cap, and hardware
can change results; these data do not establish model-wide inability.

Future prompt tuning against these public cases is development, not held-out
evaluation. Fresh documents, unseen questions, independent review, more stress
cases, and end-to-end deployment measurements are required for stronger claims.
