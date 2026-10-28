# Third-party material

The root MIT license covers original benchmark code, documentation, authored
questions, and review annotations. It does not relicense third-party model
weights, native template material, generated model responses, upstream source
text, or external packages. Preserve applicable upstream terms.

## Source booklet

FEMA / U.S. Fire Administration, *Fire Safety for Older Adults*, FA-221,
August 2024. Source: <https://www.usfa.fema.gov/downloads/pdf/publications/fa_221.pdf>.
USFA's [publication help](https://apps.usfa.fema.gov/publications/help) identifies
its catalog publications as public domain apart from the Sesame Street kit.
The supplied extracted passages come from this booklet. Publisher names are
source credits, not an endorsement. The original PDF is linked, not bundled.

## Models and templates

Weights are not distributed. Their upstream repositories and immutable revision
links are in `data/models.json`. Each model's use remains subject to its terms.

- Qwen3.5: Apache-2.0; retained native template material with tools disabled and
  thinking forced off. Apache license text is in `licenses/apache-2.0.txt`.
- MiniCPM5-1B: Apache-2.0; retained native template material with tools disabled
  and thinking forced off. The same Apache license text applies.
- LFM2 / LFM2.5: model cards identify the Liquid AI LFM Open License v1.0.
  See the [RAG model card](https://huggingface.co/LiquidAI/LFM2-1.2B-RAG-GGUF)
  and [Instruct model card](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF).
  `templates/plain_chat.jinja` is a short text-only ChatML renderer; the model
  weights retain their upstream terms.
- LFM3: the text and Omni checkpoint repositories use the LFM Open License
  v1.0. Its retained license text is `licenses/lfm-open-license-v1.0.txt`.
  Native templates are retained with tools/thinking disabled; source revisions
  and original/retained hashes are in `data/template-sources.json`.

Template files are included for reproducing the measured configurations.
Full pinned model metadata is retained; required technical repository, model,
package, and API names are intentional.

## Runtime and evaluation sources

The reference runtime is [llama.cpp](https://github.com/ggml-org/llama.cpp),
an external dependency, not bundled here. The refreshed LFM3 comparison uses a locally installed,
compatible packaged llama.cpp backend, recorded by build and binary hash in
the runtime cohort protocol; that executable is not redistributed. The runner uses Python's
standard library. The original retrieval used MiniLM, ONNX Runtime, tokenizers,
NumPy, and SQLite; their binaries and encoder weights are not bundled.

Evaluator references are linked in `data/fire-safety-v1/external-references.json`.
No substantial copies of those reference pages are distributed. Generated model
responses are retained verbatim as evaluation evidence; they are not certified
factual guidance. Related projects are credited in docs/RELATED_WORK.md; none
of their datasets, implementations, or logos are bundled.
