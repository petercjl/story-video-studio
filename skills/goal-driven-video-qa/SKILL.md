---
name: goal-driven-video-qa
description: Inspect a video against quality goals inferred from the current conversation, explicit user request, prompt, script, storyboard, reference media, prior test results, and delivery requirements. Use for 视频质检, AI-generated video review, casting or age checks, character/product/scene consistency, action and spatial continuity, subtitles or unwanted text, dialogue/audio/accent review, pacing, technical specifications, prompt adherence, or A/B generation loops. Dynamically choose inspection modalities and sampling depth, produce timestamped evidence and coverage limits, and remain read-only unless the user separately authorizes changes or regeneration.
---

# Goal-Driven Video QA
## Distribution preflight

Before the first workflow action in each conversation, run `story-video-studio preflight --agent <codex|sealseek> --json` using the current host identity. If the CLI reports an update, reload this Skill from the exact canonical path returned by preflight before continuing. If the CLI is unavailable or the suite is incomplete, return the structured dependency error and installation command instead of running a stale or partial workflow.


Inspect only what the quality goal requires, but inspect it deeply enough to support the verdict. Derive the goal from context before asking the user to restate information already available.

## Main Line

1. Resolve the video and all available context.
2. Convert the context into a testable QA contract.
3. Choose modalities, depth, sampling, references, and tools.
4. Collect deterministic evidence.
5. Inspect evidence semantically and escalate around suspected failures.
6. Run an adversarial coverage pass.
7. Report verdicts, timestamps, confidence, coverage, blind spots, and next experiment.
8. Return to the relevant earlier step whenever evidence is insufficient.

Default to read-only. Do not modify prompts, edit video, submit generation tasks, upload private media, or spend API credits unless the user separately authorizes that action.

## 1. Resolve Inputs From Context

Require a video. Infer the quality target from the current request and nearby context, including:

- explicit acceptance criteria;
- the prompt used to generate the video;
- story, script, shot list, or storyboard;
- character, scene, product, or style references;
- technical delivery requirements;
- the user's previous approval or rejection and stated reasons;
- invariants from an A/B loop.

Do not force the user to fill a form. Ask only when a missing choice would materially change the inspection. If the target says “match the reference” but the reference is unavailable, mark that criterion `not_verifiable`; do not invent ground truth.

## 2. Build The QA Contract

Before extracting evidence, write an internal contract with one row per criterion:

```text
Criterion:
Expected state:
Failure condition:
Required modality: metadata / visual / temporal / text / audio / comparison
Evidence needed:
Inspection depth:
Reference source:
Tolerance:
```

Separate observed facts, perceptual judgments, causal hypotheses, and user taste. A causal explanation is a hypothesis until an experiment supports it.

Read [references/goal-routing.md](references/goal-routing.md) when choosing modalities or depth.

## 3. Plan Inspection Depth

Use `auto` unless the user specifies a budget:

- `quick`: metadata plus sparse reconnaissance for a simple binary target.
- `standard`: scene-aware and uniform coverage plus target close-ups.
- `deep`: dense target windows, native-resolution crops, identity and continuity tracking.
- `forensic`: frame-level or sub-second sampling, A/V sync, transient artifact localization, or exact comparison.

The profile is a starting point, not a ceiling. Escalate locally when the first pass finds ambiguity or risk. Do not call a six-frame contact sheet a full-video review.

Always record:

- video duration and technical metadata;
- number of inspected frames and sampling interval or strategy;
- densely inspected time ranges;
- whether original-resolution details were viewed;
- whether audio, OCR, ASR, or reference comparison was performed;
- uncovered or unverifiable areas.

## 4. Collect Deterministic Evidence

Prefer local processing. Detect `python3`, `ffprobe`, and `ffmpeg` rather than assuming paths. Use the bundled script for repeatable evidence collection:

```bash
python3 scripts/collect_video_evidence.py VIDEO \
  --output-dir OUTPUT_DIR \
  --uniform-count 15 \
  --timestamp 2.5 \
  --dense-window 10:14:0.25 \
  --scene-threshold 0.30 \
  --contact-sheet-columns 5
```

Add `--extract-audio` only when the QA contract needs audio. Run `--help` for all options.

The script creates `manifest.json`, selected evidence files, and an optional contact sheet without interpreting quality. It samples against the decodable video stream duration rather than a longer audio/container duration. Use a new or empty output directory; preserve source media unchanged.

If the runtime lacks the required tools, use an equivalent local capability or report the unsupported evidence branch. Read [references/runtime-adapters.md](references/runtime-adapters.md) before claiming a semantic visual or audio pass.

## 5. Inspect By Modality

### Visual And Casting

Start with whole-video reconnaissance, then inspect every relevant face, object, scene, or shot at sufficient resolution. For casting, assess the requested screen impression rather than claiming a person's true demographic facts. Check age impression, role separation, styling, expression, and cross-shot identity.

### Temporal Action And Continuity

Use adjacent frames or dense windows. Check the full action chain, character and prop states, spatial sides, cut boundaries, transient deformations, and whether a failure occurs between sparse samples.

### Product Or Reference Fidelity

Load the actual references. Compare every product/reference appearance, not only the cleanest frame. Treat structure, proportions, component relationships, materials, colors, markings, and placement as reference-controlled facts.

### Text And Subtitles

Scan the entire duration at a density capable of catching short overlays. Use OCR only as supporting evidence; visually confirm positives and likely false negatives. Distinguish prohibited subtitles from story-world text when the QA contract does.

### Audio

Extract audio only when required. Use metadata, waveform/loudness tools, ASR, diarization, and sync checks as available. A transcript can verify words, not accent naturalness, timbre appeal, age impression, acting quality, or emotional truth. If the runtime cannot listen perceptually, label those criteria `human_listening_required`.

### Technical Delivery

Use metadata and deterministic checks for codec, dimensions, aspect ratio, duration, frame rate, audio presence, corruption, and other measurable requirements.

## 6. Escalate And Challenge The First Impression

When a criterion may fail:

1. inspect the suspected interval more densely;
2. view original-resolution frames or relevant crops;
3. compare earlier and later states;
4. check whether another modality changes the interpretation;
5. search for counterexamples elsewhere in the video.

Before finalizing, ask:

- Could the failure occur between sampled frames?
- Did I inspect every appearance of the target?
- Am I confusing absence of evidence with a pass?
- Am I treating ASR, OCR, or metadata as perceptual proof?
- Does the reference actually support the expectation?
- Did user feedback reveal a failure my first method missed?

If evidence remains insufficient, return to planning or report uncertainty. Never upgrade uncertainty to `pass` for convenience.

## 7. Report With Traceable Evidence

Read [references/report-contract.md](references/report-contract.md). Every material issue should identify:

- expected state;
- observed state;
- timestamp or interval;
- severity;
- confidence;
- evidence inspected;
- possible cause, explicitly labeled as hypothesis;
- recommended next verification or controlled change.

Lead with the overall result, then criterion verdicts, coverage, limitations, and next experiment. Use `pass`, `fail`, `partial`, `uncertain`, `not_tested`, `not_verifiable`, or `human_review_required`.

## 8. Support Controlled Loops

When the request is part of a prompt-generation-review loop, read [references/loop-protocol.md](references/loop-protocol.md).

Keep generation variables traceable: prompt version, model, seed when available, duration, ratio, resolution, references, task id, and output file. Propose the smallest change that tests the strongest hypothesis. Do not regenerate until authorized.

Promote a lesson into a reusable Skill rule only after evidence shows it generalizes. Keep one-off fixes in the project or test log.

## Branches And Return Rules

- Missing video: resolve the path or ask for the file, then return to Step 1.
- Vague goal with rich context: infer criteria and continue; show assumptions in the report.
- Vague goal without context: perform technical integrity plus reconnaissance, label the provisional scope, and ask one focused follow-up only if necessary.
- Missing reference: mark reference-dependent criteria `not_verifiable`; continue with independent checks.
- Suspected transient failure: increase temporal density and return to Step 5.
- Suspected face/product mismatch: inspect all appearances at original detail and return to Step 5.
- Audio target without perceptual audio capability: run measurable checks, mark subjective items for human listening, and continue to Step 7.
- User rejects the QA conclusion: treat the feedback as new evidence, identify the missed criterion or insufficient coverage, revise the method, and rerun from Step 2.

## Completion Gate

Do not finish until:

- criteria were derived from context and made testable;
- inspection depth matches the risk;
- deterministic metadata and evidence manifests exist when tools allow;
- suspected failures were inspected more densely;
- verdicts cite timestamps and evidence;
- coverage and blind spots are explicit;
- subjective audio claims are honest;
- no source media or prompt was mutated without authorization;
- loop recommendations preserve controlled experimentation.
