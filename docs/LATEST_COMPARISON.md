# LFM3 text-generation comparison

## What ran

Version 0.2.0 adds:

- LFM3-1.7B Q4_K_M: the post-trained text checkpoint.
- LFM3-Omni-2B Q4_K_M: text input and text output, with no multimodal projector
  or audio codec loaded.
- Qwen3.5-0.8B Q4_K_M rerun as a baseline on the same compatible runtime.

Both new checkpoints were already available locally. Their weight sizes and
SHA256 values were checked against the official pinned GGUF repositories before
execution. Each model received the exact original 40 message lists in their
original order, twice, with an identical unscored warmup before each run.

The original six configurations, all 480 outputs, and their judgments remain
unchanged. `data/original-snapshot.json` pins those original evidence files.
The new group adds 240 outputs. This is nine measured configurations across two
runtime groups, not nine distinct model checkpoints.

## Results

| Configuration | File MB | Document /20 | Boundary /8 | Handling /4 | Core /32 | Supplement /8 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.5-0.8B Q4_K_M | 532.5 | 19 | 7 | 2 | 28 | 2 |
| LFM3-Omni-2B Q4_K_M, text only | 1099.6 | 20 | 6 | 2 | 28 | 3 |
| LFM3-1.7B Q4_K_M | 1099.6 | 20 | 2 | 2 | 24 | 3 |

Counts are identical between the two runs. Both LFM configurations improve the
document subset relative to this baseline, while losing more boundary tasks.
No configuration passes every core requirement. The equal core total for Omni
and Qwen hides different strengths; inspect the separate group counts.

File size is reported in decimal MB and does not measure runtime RAM.
Omni's total multimodal deployment footprint is larger than
the text-generation file measured here. These data say nothing about its
recognition, speech synthesis, image understanding, or headset performance.

## Thinking was disabled

All three servers used `--reasoning off`. The LFM3 native templates were pinned
and retained, with `tools=[]` and `enable_thinking=false` prepended. The original
system prompt also instructs the model not to show reasoning or call tools.
No thinking-enabled run was substituted.

Nevertheless, the text model emitted literal `</think>` markers in
`heater_shutoff` and `co2_action` in each run: 4/80 responses. It also frequently
used self-directed deliberation-style prose. The official
[text model card](https://huggingface.co/LiquidAI/LFM3-1.7B) notes that disabling
thinking can be inconsistent. The report distinguishes configured controls from
observed output behavior. We did not remove markers or hide preceding text.

Omni and the Qwen baseline tested on 28 October emitted no explicit thinking
markers. This is a marker check, not an exhaustive proof that no answer contains reasoning-style
prose. No structured tool calls were returned by any of the three candidates.

The text model reached the 192-token limit in 14/40 and 15/40 responses; Omni
in 2/40 and 2/40; the baseline in 0/40 and 0/40. Cutoffs remain scored as returned.
Some incomplete self-directed discussions failed the requirement to give a
completed brief refusal, even though they did not provide an outside-topic
answer. Conflict recognition alone did not earn a pass when the text model
explicitly endorsed the incorrect synthetic yearly testing instruction.

## Review and repeatability

Every distinct new LFM response was read against the prewritten expected
behavior, actual supplied passages, and official evaluator references. All 40
Omni answer texts match between runs. The text model matches 39/40; its changed
deaf-alert answer was reviewed separately and contains the required types before
cutoff. Citation misattributions and material extra advice are flagged in notes.

All 80 Qwen outputs from 28 October match their original corresponding answers
exactly. Its judgments were reused only after byte equality and answer SHA256
were verified. Independent expert review and inter-rater agreement remain absent.

The CO2 mechanism answers illustrate why the entire reply matters: both LFM
outputs identify oxygen displacement but add misleading suitability/reignition
claims, so they do not receive full factual credit. The original OSHA reference
and the [Canadian Centre for Occupational Health and Safety](https://www.ccohs.ca/oshanswers/safety_haz/fire_extinguishers.html)
support checking those additional claims. These references are evaluator-only.

## Runtime group and reproduction

The Homebrew build used for the original run is too old for these checkpoints.
The new run uses the already-installed compatible llama.cpp packaged backend:
`0.7.0-dev (build 1, commit a469940)`, AppleClang 15.0.0, Darwin ARM64.
Its binary SHA256 is pinned in
`data/cohorts/2026-10-28-compatible-runtime.json`.

Controls remain: 4 CPU threads, 1 slot, 4096-token context, 99 GPU layers,
temperature 0, top-k 20, top-p .95, min-p 0, repeat penalty 1, max output 192,
thinking off and no tools. Model-native templates differ, as in the original
benchmark. The Apple M3 Pro has 18 GB unified memory. Existing application
servers were left running; host state and caching remain timing confounds.

Select the report's 28 October tests for within-group timing comparisons. Do not
equate old and new runtime timings. The two runs remain separate, and text
length differs substantially. No randomized order, thermal isolation, peak-RAM
measurement, or first-token/Quest measurements were performed.

For a fresh reproduction, choose new result identities so existing files cannot
be overwritten. Download pinned files from `data/models.json`, provide a
compatible server binary, and run:

```sh
python3 run_local_models.py --server /path/to/compatible/llama-server --port 1236 \
  --output-root runs/my-comparison --cohort-id my-comparison \
  --hardware 'describe your hardware' --memory-gb 18 --backend Metal
```

Replace the example hardware, memory, and backend with your actual configuration.
The runner owns and terminates only the process it starts. It refuses an occupied
port, verifies loaded weights, and records runtime/template hashes. Private logs
stay in the ignored `.runtime` directory. Results and their protocol default to
the ignored `runs/local-comparison` directory. The script refuses existing output
files; choose a fresh output directory and cohort ID for another reproduction.
It does not overwrite or automatically publish the official reference runs.
See docs/REPRODUCE.md for manual execution with the generic
runner when a different runtime is used.
