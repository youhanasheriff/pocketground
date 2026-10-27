# Contributing

Start by reading README.md and docs/METHODOLOGY.md. The reference data is a
versioned evidence snapshot; preserve it.

Useful contributions include a fresh domain dataset with evidence, a new pinned
model configuration, an independent review of existing judgments, a documented
failure case, or measurements on a real target device.

For a new result, provide model repository/revision/filename/bytes/SHA256,
template hash, runtime build, hardware/backend, sampling/context/output limits,
exact inputs, complete raw responses, timing definitions, review hashes and
notes, and an explicit description of any deviation from the reference protocol.
Use a distinct result identity; do not replace another run or silently alter its
prompt. Keep API errors, refusals, and length cutoffs visible.

For a scoring correction, identify the exact case and answer hash, explain the
disputed judgment, and provide supporting source passages or authoritative
references. Preserve the old judgment in the correction history and rebuild
all affected summaries. A model's assertion is not its own gold reference.

Run the automated checks:

```sh
python3 -m unittest discover -s tests -v
python3 build_report.py
python3 freeze_manifest.py
python3 pocketground.py verify
```

Inspect the report at desktop and phone widths, exercise its filters and answer
links, and verify that changed charts still agree with the source records.
Do not commit credentials, local environment/runtime files, personal paths,
unlicensed source material, or model weights. Use links and hashes for weights.

The current public cases are development-visible. Fresh held-out evidence is
needed to claim an improvement beyond tuning to this suite.
