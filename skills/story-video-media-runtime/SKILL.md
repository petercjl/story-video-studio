---
name: story-video-media-runtime
description: Route story-video image and video generation through one platform-neutral request contract on Codex or SealSeek/OpenClaw. Use when an upstream Skill needs real reference images, keyframes, or video clips without embedding a platform tool name, provider command, or machine path.
---

# Story Video Media Runtime
## Distribution preflight

Before the first generation action in each conversation, run `story-video-studio preflight --agent <codex|sealseek> --node video-generation --json` using the current host identity. If the CLI reports an update, reload this Skill from the exact canonical path returned by preflight before continuing. If preflight fails, return its structured repair instruction. Provider capability and credentials are checked again by the selected host adapter before submission.


Normalize image and video generation across supported Agent hosts. This Skill owns platform detection, adapter selection, video model routing, native-call normalization, and durable artifact materialization. It does not write stories, design shots, approve assets, or judge creative quality.

## I -> S -> O

**Input:** a `story-video-media-request@1.x` containing `request_id`, `media_kind`, prompt, delivery settings, ordered references with roles, generation scope authorization, and video-routing signals when applicable.

**Strategy:** identify the host from its advertised Agent/runtime identity; load `capabilities.json` and the exact matching adapter; validate feature coverage; select a video model family from the versioned routing policy; invoke only the mapped native capability; normalize its result; materialize every returned remote artifact into the caller's project directory without overwriting an existing file; then return hashes, provider metadata, cost evidence, warnings, and a stable error when any contract cannot be satisfied.

**Output:** a `story-video-media-result@1.x` with `ok`, request/platform/adapter identity, selected route, native task/provider metadata, immutable remote source URL when present, local artifact path, SHA-256, byte size, cost evidence, warnings, and a standard error on failure.

## Main Flow

1. Read the complete media request. Reject missing prompt, media kind, output path, generation authorization, or required reference roles before a paid call.
2. Detect `codex` or `sealseek-openclaw` from the host's advertised runtime context. Do not infer a platform from filesystem paths, installed applications, or tool names found on disk.
3. Load `capabilities.json`, then load exactly `adapters/<platform>.json`. Confirm every required feature for this request is mapped with `tested` or `implemented` status. Return `CAPABILITY_UNAVAILABLE` or `FEATURE_UNSUPPORTED` for a gap; never substitute a weaker generation mode.
4. Normalize ordered references. Each reference contains `uri` or readable local path, `role`, optional `asset_id`, SHA-256 when locally available, and approval evidence supplied by the caller. Keep the order stable. References carry identity and structure; prompt text carries action, timing, camera, emotion, sound, and concise reference locks.
5. For an image request, apply adapter defaults only when the caller omitted a setting. Preserve an explicit user model choice. Generate exactly the authorized candidate count.
6. For a video request, read [video model routing](references/video-model-routing.md). On a host whose adapter delegates routing to its installed provider runtime, keep ordinary selection automatic and record that runtime's effective decision. On a host whose adapter requires semantic routing, run `scripts/select_video_model.py` with the complete signals and map the selected family through that adapter. An explicit user choice wins when the combination is supported.
7. Invoke the native capability using only fields advertised by its live schema. Save the effective native request excluding credentials. A paid call is allowed only for the exact candidate or clip scope authorized by the user or upstream review gate.
8. Normalize the native result. Preserve task ID, returned URLs, model/provider metadata, billed-credit text or structured cost when available, and raw warnings. Do not translate a provider failure into a creative QA failure.
9. Materialize each remote artifact with `scripts/materialize_artifact.py`. Refuse to replace an existing target. Verify non-empty content, reject obvious HTML/error bodies, calculate SHA-256 and record bytes and media kind. Video callers perform their own `ffprobe` and visual review after this transport gate.
10. Return the normalized result to the caller. The caller owns technical inspection, creative QA, user approval, package/index updates, and project-state transitions.

## Platform Rules

### Codex

- Load the current Codex adapter and its exact dependencies at execution time.
- Keep ordinary video model selection automatic when the adapter delegates it to the installed provider runtime.
- Local native paths, credentials, tool names and model IDs stay in the adapter or dependent runtime, never in this core.

### SealSeek/OpenClaw

- Load the current SealSeek/OpenClaw adapter and use its declared image default when the caller omitted a model.
- Route video semantically to Seedance 2.0 or 2.5, then use the adapter's current native alias.
- SealSeek normally returns public artifact URLs and billed-credit text. Preserve both, then materialize the artifact locally before reporting success to the caller.
- Inspect the live native schema before every reference-based call. Reference-image video remains `implemented`, not `tested`, until a real reference-based generation and artifact inspection pass.
- Speaker-specific audio reference is a separate conditional capability. The SealSeek adapter currently marks it unresolved; when a clip requires an already-approved voice, return `FEATURE_UNSUPPORTED` rather than dropping the audio binding.

## Normalized Contracts

Read [media request and result contracts](references/media-contract.md) before integrating a caller. The core field names remain platform-neutral. Adapters may translate them but may not remove required roles, approval evidence, output persistence, or authorization boundaries.

## Failure Behavior

- `CAPABILITY_UNAVAILABLE`: no adapter or native implementation is available.
- `FEATURE_UNSUPPORTED`: the adapter cannot satisfy a required mode, reference role, duration, resolution, or model combination.
- `PAID_ACTION_NOT_AUTHORIZED`: generation scope was not explicitly authorized.
- `PROVIDER_FAILURE`: the native service failed before a valid artifact was returned.
- `OUTPUT_CONTRACT_FAILED`: the result cannot be normalized or materialized.
- `TARGET_EXISTS`: the requested local artifact path already exists and replacement was not authorized.

Preserve the failed request, native response summary, and next validation needed. Return control to the caller without rewriting project approval state.

## Completion Gate

Complete only when platform selection is explicit, required adapter features pass, the effective request and route are recorded, every returned artifact has a verified local path and SHA-256, cost evidence is retained when supplied, and the caller receives one normalized result. Compatibility labels must match evidence: `tested` requires a real native generation and inspected artifact; `implemented` means the mapping exists but still needs that target-runtime proof.
