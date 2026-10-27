# Related work

Reviewed on 27 October 2026. These projects establish relevant prior work;
their scores use different datasets, prompts, models, and grading rules and
must not be directly ranked against PocketGround.

## SLM RAG Arena

[Official arena](https://huggingface.co/spaces/aizip-dev/SLM-RAG-Arena)
and [published app source](https://huggingface.co/spaces/aizip-dev/SLM-RAG-Arena/tree/main).

The app identifies its scope as small models under 5B parameters. Users compare
anonymous document-context answers and vote for a preferred response, a tie,
or neither. Its useful design pattern is the ease of comparing exact answers.
Preference votes and rubric-based correctness are different measures.

PocketGround uses visible expected behaviors, fixed-context inputs, and separate
task outcomes. It does not present an imitation preference leaderboard or
claim crowd voting has occurred.

## MiniRAG and LiHua-World

[Official repository](https://github.com/HKUDS/MiniRAG)
and [paper](https://arxiv.org/abs/2501.06713).

MiniRAG is a lightweight RAG method. Its LiHua-World dataset targets on-device
RAG using a virtual user's chat history, with answers and supporting documents
for single-hop, multi-hop, and summary questions. Published comparisons include
small-model configurations and a proprietary baseline, so it is not exclusively
a tiny-model benchmark. Its useful pattern is recoverable supporting evidence.

PocketGround retains paragraph text and source page links for each answer, and
clearly marks synthetic conflict/injection passages. No LiHua-World data or
MiniRAG implementation is copied into this release.

## SLM-RAG-EVAL / Little Brains, Big Feats

[Official repository](https://github.com/SibNN/SLM-RAG-EVAL)
and [paper](https://arxiv.org/abs/2606.30062).

This research investigates compact models during the generation stage of RAG.
Its repository describes a public 400-example subset and a proprietary
100-example subset omitted for licensing reasons, with model outputs and
evaluation files in a reproducibility package. Its useful pattern is separating
publicly reproducible evidence from unavailable material.

PocketGround publishes the frozen inputs and recorded outputs for all its
cases. Model weights and the original PDF are restored from pinned source links;
they are not required simply to inspect the report.

## Positioning

PocketGround 0.1.0 emphasizes quantized model files below 1 GB, fixed retrieved
context, clear boundary/stress cases, and inspectable judgments. It is an
exploratory first release. This description makes no claim of being the first
small-model RAG benchmark, the largest, or a general reliability standard.
