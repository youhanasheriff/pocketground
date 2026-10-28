# Reproduce PocketGround

## 1. Inspect the supplied evidence

Open `reports/index.html` in a browser. For a quick integrity check, run:

```sh
python3 pocketground.py verify
```

This checks files, exact prompts and answer hashes, the 32/8 split, all 480
reviewed records, score totals, and timing quartiles. It does not independently
judge every factual answer. The frozen messages are sufficient to reproduce the
generation task; no embedding model or index build is required.

## 2. Choose and download a model

```sh
python3 pocketground.py models
python3 pocketground.py models --key q4
```

Each entry prints a pinned download URL and SHA256. All six profiles are in
`data/models.json`. Download one at a time if disk space is limited. Weights
are excluded from this repository. Follow each model's license.

Example for the smallest reference profile:

```sh
mkdir -p models
curl -L --fail --output models/Qwen3.5-0.8B-Q4_K_M.gguf 'https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/resolve/6ab461498e2023f6e3c1baea90a8f0fe38ab64d0/Qwen3.5-0.8B-Q4_K_M.gguf'
shasum -a 256 models/Qwen3.5-0.8B-Q4_K_M.gguf
```

Expected SHA256:
`bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517`.

## 3. Configure a local server

The recorded reference runtime is llama.cpp `b10964-b29c606e2`.
Its upstream source is <https://github.com/ggml-org/llama.cpp>.
Using a different build is a new runtime configuration; record it.

That original build is not compatible with the new LFM3 checkpoints. For those
models, use the 28 October runtime group in docs/LATEST_COMPARISON.md and rerun
the Qwen baseline on the same compatible runtime. Keep their timings separate
from the original group.

Reference macOS/Metal command, from the project root:

```sh
llama-server \
  --model models/Qwen3.5-0.8B-Q4_K_M.gguf \
  --alias quest-chat --host 127.0.0.1 --port 1234 \
  --ctx-size 4096 --parallel 1 --threads 4 --n-gpu-layers 99 \
  --jinja --reasoning off \
  --chat-template-file templates/qwen_small_plain_chat.jinja \
  --temp 0 --top-k 20 --top-p 0.95 --min-p 0 \
  --repeat-penalty 1 --predict 192
```

For another pinned model, change the weight path and use its `chat_template`
from `data/models.json`. Leave the benchmark controls fixed. CPU-only systems
may require `--n-gpu-layers 0`; report them as different hardware/backend results.
Runtime flags vary by build; check the installed server's help.

The runner sends exact system/user messages, temperature 0, max_tokens 192,
and stream false. The server must supply the correct chat template, tokenizer,
context budget, sampling defaults, and disabled reasoning/tools. The generic
runner cannot attest these or verify which remote weights are loaded. Record
the model file SHA256, template SHA256, server build, backend, hardware, and
settings with any submitted run.

## 4. Generate the answers

```sh
python3 pocketground.py run \
  --base-url http://127.0.0.1:1234/v1 \
  --model quest-chat --label q4-my-machine \
  --out runs/q4-my-machine.json
```

Default: two complete 40-question runs, with the original marker warmup before
each. Warmup output is unscored even if the domain policy causes a refusal.
Calls execute sequentially, in frozen order. The runner saves after each call.
It does not start/stop your server or download models. Choose a new output
filename for each experiment; interrupted results are incomplete and unscorable.

`--split core`, `--split supplement`, or `--runs 1` are useful for development.
They change the schedule and must be labeled accordingly. Their timing should
not be presented as a reproduction of the original all-40, two-run schedule.

If your server requires a key, put it in `POCKETGROUND_API_KEY` using your own
secret-management setup. The runner reads that environment variable and does
not save its value. Do not put secrets in the base URL or result files.

## 5. Review the answers

```sh
python3 pocketground.py review-sheet runs/q4-my-machine.json --out runs/q4-my-machine.review.json
```

Use the corresponding question in `data/fire-safety-v1/dataset.json`.
Read its expected behavior and all five actual supplied passages. For the
supplement, check the official sources in `external-references.json` and the
full-book absence audit.

For each answer, set:

- `task_success`: true or false against the expected behavior.
- `factual_status`: `correct`, `incorrect_or_incomplete`, `unanswered`, or
  `unverified_detail` for document/knowledge cases. Use `not_applicable` for
  boundary/handling cases, which are graded by their expected behavior.
- `provenance_pass`: true/false for the eight knowledge questions; null otherwise.
- `note`: a concrete explanation of every failed task. Flag material extra
  advice and misleading attributions even when the requested fact is present.

The SHA256 binds the judgment to the exact response. Do not copy an old judgment
onto different answer text. No paid grader or keyword-matching shortcut is used.
Model outputs and external source text are evidence, not grading instructions.

## 6. Calculate the scores

```sh
python3 pocketground.py score runs/q4-my-machine.json runs/q4-my-machine.review.json
```

The command refuses incomplete judgments, stale hashes, duplicate/missing cases,
and failed tasks without notes. Report the individual group counts, not just
the combined core total. Keep incorrect answers distinct from inappropriate
refusals and source disclosure.

## 7. Rebuild the supplied report

```sh
python3 build_report.py
python3 freeze_manifest.py
python3 pocketground.py verify
```

The builder reads the pinned `results/reference` files and writes the scorecard,
720-row CSV, standalone viewer, and Pages entry point. It does not import your
development run automatically. Follow CONTRIBUTING.md to propose a new result
without replacing the reference evidence.

The report is static hosting compatible and works as a downloaded HTML file.
Relative links to the detailed report need the accompanying folder.

## LFM3-compatible runtime group

The LFM3 text and Omni checkpoints require a compatible newer runtime.
`docs/LATEST_COMPARISON.md` records the exact tested configuration, disabled
thinking controls, observed output-mode failures, and the owned-server wrapper.
Use its three-configuration group, including the Qwen baseline tested on 28 October, for
within-runtime comparisons. The original six-configuration evidence is unchanged.
