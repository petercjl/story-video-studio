---
name: ai-video-reference-asset-studio
description: Build and review reusable character, environment, prop, and shot-keyframe images for AI video production from an approved production package or a direct brief, while consuming approved textual style controls. Use when planned visual assets or formal shot keyframes must become real, traceable images. Do not use for story writing, storyboard planning, video prompts, or video generation.
---

# AI Video Reference Asset Studio
## Distribution preflight

Before the first workflow action in each conversation, run `story-video-studio preflight --agent <codex|sealseek> --json` using the current host identity. If the CLI reports an update, reload this Skill from the exact canonical path returned by preflight before continuing. If the CLI is unavailable or the suite is incomplete, return the structured dependency error and installation command instead of running a stale or partial workflow.


Turn approved visual-production intent into real, reviewed reference images and formal shot keyframes. Upstream planning decides what the story and shot need; this Skill normalizes the work, protects source references, compiles task-specific prompts, generates one controlled candidate at a time, inspects it, and records approval before dependent work continues.

## I -> S -> O

**Input:** one of: an `ai-video-reference-asset-request@1.x` from a shot/prompt designer, another approved visual-production manifest, or a direct character/environment/prop/keyframe brief; optionally an exact asset ID or name; plus available source references, an output directory, and generation authorization when actual media is requested.

**Strategy:** normalize the selected task and delivery profile; preserve source task IDs and consumers; distinguish hard from advisory dependencies; apply source and identity gates; select the character, environment, prop, style, or shot-keyframe branch; compile operator notes separately from model prompt text; generate through the current platform adapter; visually inspect every result; record technical QA and user approval separately; then expose only approved images to downstream consumers.

**Output:** an `ai-video-reference-asset-package@1.4.0` with an explicit image form and authority split, source/work-order traceability, prompts, attempts, QA, approval, relative artifact paths, and a non-destructive upstream binding patch. An intentional multi-view/state board is one approved master image plus deterministic panel crops recorded as intermediate technical outputs. Actual images are required only when generation is authorized.

## Scope

This Skill owns reusable reference assets:

- character base identity, required views, and story-state variants;
- empty environment masters and only the additional spatial views demanded by consumer shots;
- important props and their required operational/story states;
- approved textual style controls that environment assets inherit for light, color, material rendering, contrast, texture, and capture character.
- formal shot keyframes already planned upstream, generated from one composition sketch plus the approved reusable assets and style controls named by that keyframe task.

This Skill does not design shots or decide how many keyframes a shot needs. Generate exactly the selected upstream keyframe task by default. Add opening, action, or result frames only when the upstream package already requests them or the user separately authorizes a revision after testing.

## Knowledge Routing

Do not load the knowledge layer merely because the Skill was selected. At the first asset-production judgment, read [references/SCHEMA.md](references/SCHEMA.md), [references/index.md](references/index.md), and the recent part of [references/log.md](references/log.md), then follow [references/queries/build-reference-assets.md](references/queries/build-reference-assets.md). Return to Main Flow step 3 with a normalized asset strategy.

## Main Flow

1. Resolve the input and output root. For an `ai-video-reference-asset-request`, read [the reference request contract](references/topics/reference-request-contract.md) and run `scripts/extract_reference_request.py --input ... --output ...` with `--all`, repeated `--asset-id`, or an exact `--asset-name`. This is the direct, primary interface for reference needs inferred from video shots. The user may request every reusable image asset, one named asset, or one named formal keyframe. Select IDs and names exactly; trim only surrounding whitespace, brackets, and quotation marks. Preserve the original request unchanged.
2. Check whether requested target files already exist before writing. Fix the task folder, version folder, image filename, package path, and intermediate-file directory before generation. Create a new version or a verified recovery copy unless replacement of that known file was explicitly authorized.
3. Normalize the work order and select the delivery profile before compiling a prompt. For reusable assets, retain the existing character/environment/prop/style rules. For `shot-keyframe`, read [references/topics/shot-keyframes.md](references/topics/shot-keyframes.md), require one real composition sketch and every approved reusable asset named by the upstream task, and retain exactly one requested keyframe unless upstream or the user explicitly adds more. A sketch is a composition authority only; it does not supply identity, wardrobe, materials, lighting, color, or finished-image style. Approved character, environment, prop, state, and textual style controls supply those finished-image facts. If the sources cannot be combined without contradicting the shot task, return `KEYFRAME_SOURCE_CONFLICT` rather than inventing a new shot.
4. Classify dependencies as `hard`, `advisory`, or `unresolved`. Identity, structure, and geometry sources are hard. For a same-kind derivative, follow the dependency chain to every original root: character → identity root, environment → geometry root, prop → structure root. Resolve each root only from an approved asset package and a real file. An approved textual style control is advisory and resolved without an image file because it controls look rather than identity or geometry.
5. Apply source gates. Real products and recognizable people require approved, authorized sources when the asset is meant to preserve them. A new fictional character may start from text. Under `higgsfield-three-panel`, its first candidate is the complete three-panel identity sheet; user approval makes that sheet the only identity root. A single portrait or full-body study may be retained as calibration evidence but is not the completed character asset and cannot enter upstream bindings.
6. Choose one branch and compile one image request using the routed knowledge. For a derivative, require every `authoritative_references` entry to be `resolved`; pass its exact root `path` to image generation and record its SHA-256. Never substitute the most recent candidate, a derivative, or an unapproved file. For a shot keyframe, pass the pencil sketch first as `composition`, then only the approved asset masters or panel crops needed by that shot. Translate the sketch into composition facts and explicitly exclude its paper, pencil, monochrome, labels, borders, temporary faces, temporary costume, and unfinished rendering from the final image. Put reference files, interface parameters, purpose, consumers, authority roles, and acceptance checks outside the model prompt. Put only visible content, shot framing, blocking, pose/action state, spatial relationship, light, material, style, and concise reference locks inside it.
7. Before actual generation, resolve exact `story-video-media-runtime` from the host catalog or configured Skill roots, load its complete current `SKILL.md`, media contract, capability manifest and matching platform adapter, and submit one platform-neutral image request. The request contains the effective prompt, ordered approved references with authority roles and hashes, aspect ratio, resolution, planned unused output path and exact paid candidate scope. Leave the model unset unless the user explicitly selected one; the runtime applies the platform adapter default. Require a normalized local artifact and SHA-256 before returning here. Then resolve `media.image.inspect` through the same runtime adapter and inspect the real image.
8. Generate one candidate for one selected asset or keyframe. Record the exact prompt actually sent to the image model, all real input files in call order, provider, parameters, returned artifact, and selection reason. Preserve failed and rejected attempts under the planned version's `intermediate/` area. For `multi-state-prop-board`, generate one coherent master sheet, then run `scripts/crop_asset_board.py` with the approved normalized crop boxes. For `shot-keyframe`, the selected output is one standalone finished cinematic frame, never a storyboard sheet, identity sheet, empty location plate, or collage.
9. Inspect the real image. Evaluate only visible evidence against asset-specific checks. Record `technical_result` separately from `user_approval`.
10. Pause at every new character/product/other identity root until the user approves it. For `higgsfield-three-panel`, approve the complete sheet only after the left body/wardrobe panel contains no face, the center direct-back panel exposes no facial features, the right frontal close-up is the sole facial authority, and body, wardrobe, background, and light all pass. Later angles or states must be generated afresh from the original approved root, not edited from or chained through a derivative.
11. Write or update the package defined in [references/topics/output-contract.md](references/topics/output-contract.md), validate it with `scripts/validate_asset_package.py`, and emit `upstream-bindings.json` without overwriting the upstream request. Return the package path and approved images.

## Branches And Returns

- `INTENTIONAL_BOARD_SELECTED`: keep one upstream row as one generating asset, define ordered panel roles and crop boxes, generate one master board, create deterministic crops, then return to step 9.
- `COMPOUND_TASK_SPLIT_REQUIRED`: create child asset IDs, exact parent traceability, variant contracts, generation order, and child dependencies only when one board cannot safely share identity, resolution, approval, or authority; return to step 4 after the split is unambiguous.
- `COMPOUND_CHILD_APPROVAL_REQUIRED`: preserve completed sibling candidates and pause before a dependent child until its declared root or surface inputs are approved.
- `ASSET_NAME_NOT_FOUND`: report the unmatched name and stop; do not guess by semantic similarity, task order, or neighboring spreadsheet rows.
- `ASSET_NAME_AMBIGUOUS`: report the matching task IDs and request a more specific name or task ID; do not select the first match.
- `STYLE_CONTROL_NOT_IMAGE_ASSET`: when the selected name resolves to a textual style-control task, explain that it is automatically applied during environment generation and stop without generating an image.
- `KEYFRAME_SKETCH_MISSING`: the selected formal keyframe has no real readable sketch binding; return to the upstream package or sketch task.
- `KEYFRAME_ASSET_NOT_APPROVED`: one or more character, environment, or prop dependencies are absent from the effective approved asset index; list them and stop before generation.
- `KEYFRAME_SOURCE_CONFLICT`: the sketch, shot specification, or approved assets require mutually incompatible composition or state facts; preserve the sources and return the conflict upstream.
- `KEYFRAME_COUNT_REVISION_REQUIRED`: the current test indicates another control frame may help; report the observed failure and request an upstream or user-approved keyframe revision instead of adding frames automatically.
- `DELIVERY_PROFILE_MISMATCH`: keep the attempt as rejected or calibration evidence, compile the required asset form, and return to step 6. Do not relabel a single-view image as a Higgsfield character asset.
- `UPSTREAM_INTENT_INCOMPLETE`: report the missing purpose, consumer, state, or spatial duty and return to the upstream planner.
- `SOURCE_REFERENCE_REQUIRED`: block that asset until an authoritative source is supplied; unrelated assets may continue.
- `ROOT_REFERENCE_APPROVAL_REQUIRED`: a root candidate exists but is not approved; report the candidate package and stop before image generation.
- `ROOT_REFERENCE_AMBIGUOUS`: differently hashed approved files claim the same root; preserve all candidates and request one authority decision.
- `ROOT_REFERENCE_MISSING`: the dependency graph identifies a root task but no usable artifact exists; return to that root asset task.
- `REFERENCE_CONFLICT`: preserve the conflicting sources and request an authority decision. Do not average identities or geometry.
- `ADVISORY_DEPENDENCY_WAIVED`: allow only an explicitly labeled exploratory candidate when a legacy style-image dependency is unavailable but an approved textual specification is sufficient; return to step 6.
- `USER_APPROVAL_PENDING`: preserve the candidate and package state, then stop before derivative generation.
- `PROVIDER_FAILURE`: preserve attempt evidence and stop or continue independent assets. Do not substitute an undeclared provider.
- `ASSET_QA_FAILED`: keep the result under `rejected/`, diagnose source/prompt/runtime cause, then regenerate from the authoritative root if authorized.

## Hard Reference Rules

- References carry identity, product structure, established location geometry, and approved object relationships. Prompt text carries task, state, viewpoint, composition, light, and facts references cannot show.
- A character, product, or other identity-sensitive derivative always points to the original approved base source. A failed, rejected, edited, angle, or state image never becomes the new root.
- Same-kind dependency traversal is recursive. A state based on an angle, or another angle based on a prior angle, still resolves to the original approved identity/geometry/structure root. Generation input and package evidence must record that root file and its hash.
- Under the Higgsfield author profile, one horizontal three-panel sheet is one intentional identity asset. The left panel carries front body proportions and wardrobe with the head/face cleanly removed; the center panel carries the direct back view with no facial features visible; the right frontal close-up is the only face and expression identity source. All panels share one character and wardrobe on one neutral continuous backdrop. A single-view image or a sheet with a second visible face is invalid for this profile.
- A `fixed-style-prompt` controls photographic register, light, palette, material rendering, contrast, and texture. Environment generation combines it with the selected environment's own spatial specification and matching scene override. It never defines character identity or reusable scene geometry.
- Legacy `style-reference-frame` and `multi-panel-style-board` packages remain readable for traceability, but ordinary production uses approved textual style controls when no style image is required.
- One attractive environment image proves only visible surfaces and relationships. Additional angles require sufficient overlapping geometry or return upstream for a spatial control asset.
- A style reference controls style only. Its person, costume, props, and location do not become story facts.
- A pencil storyboard controls composition only: shot size, camera angle, subject placement, screen direction, major overlap, action silhouette, and broad spatial relationship. Its drawing medium, monochrome palette, paper, grid, labels, temporary identity, temporary costume, and provisional prop detail never become final-frame facts.
- A formal keyframe combines authorities rather than averaging them: upstream shot/task facts define the moment; the sketch defines composition; approved character roots define identity and wardrobe; approved environment images define location geometry; approved prop masters or state crops define object structure/state; textual style controls define the finished photographic look.
- Each reference has a named role. Remove references that solve no named risk.

## Completion Gate

Complete only when every delivered asset has a stable ID, source task, and declared asset form; compound tasks use an intentional board or a justified split; board panels and crops are fully recorded; the selected delivery profile is satisfied; hard references exist; prompts and operator settings are separated; each generated candidate has a real attempt and visual QA record; identity roots have user approval; rejected or calibration outputs remain excluded from downstream bindings; the package validator passes; and compatibility claims match actual adapter evidence.
