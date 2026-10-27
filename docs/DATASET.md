# Fire Safety v1

The first PocketGround dataset uses the U.S. Fire Administration's
*Fire Safety for Older Adults*, FA-221, August 2024. It is a 24-page U.S.
home-safety booklet, not a comprehensive fire-safety textbook or a statement
of Indian legal requirements.

- [Official PDF](https://www.usfa.fema.gov/downloads/pdf/publications/fa_221.pdf)
- [Official catalog entry](https://apps.usfa.fema.gov/publications/display?id=361)
- [Public-domain guidance](https://apps.usfa.fema.gov/publications/help)

The PDF is not bundled. Download it from the original source and compare
its bytes/SHA256 with `data/fire-safety-v1/source.json`. The exact extracted
passages used by the generation benchmark are bundled. PDF page numbers
refer to file pages, starting at one.

## Files

- `dataset.json`: suite ID/version, unchanged system prompt, request settings,
  and all 40 cases. Each includes question, expected behavior, group, reporting
  split, five actual passages, original natural retrieval, exact messages,
  retrieval time, expected pages, and a SHA256 of the serialized messages.
- `source.json`: source URL, title, bytes, SHA256, retrieval date, and scope.
- `protocol.json`: the original all-40 execution protocol and prompt hashes.
- `rubric.json`: retained policy and separate grading definitions.
- `absence-audit.json`: terms and full-book checks for the eight external facts.
- `external-references.json`: official evaluator-only reference links.
- `corpus.json`: passage count, index/encoder size, and extraction repairs.

The exact-message hash is SHA256 of Python's UTF-8
`json.dumps(messages, sort_keys=True)`. It is a reproducibility identity, not
a security guarantee. Answer judgments hash the exact UTF-8 answer string.

## Adding another domain

Create a new suite ID and version. Choose its domain policy, documents, questions,
and rubric before collecting answers. Use original, unseen questions rather than
changing facts in this suite. For each case, freeze the five actual passages and
exact messages. Distinguish natural retrieval from synthetic stress mutations.
Verify which expected answers are present or absent in the full source.

Keep answerable, unrelated, uncertain, conflict, and injection cases distinct.
Do not call every missing answer a hallucination. Run the same inputs across
models, save errors and cutoffs, and have reviewers explain failures. A new
dataset should be an additional identified suite; it must not overwrite v1.

The current viewer and reference checks are scoped to Fire Safety v1. The API
runner accepts its schema through `--dataset`; multi-suite aggregation is not
implemented in this release.
