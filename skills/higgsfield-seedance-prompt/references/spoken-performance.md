# Spoken Performance Prompt Contract

Use this branch when a visible character speaks, replies, whispers, calls out, or delivers an on-screen monologue. Voice-over with no visible speaker does not require facial-performance direction.

## Default: Light Control

Write the speaking beat as one restrained performance arc:

1. **Preparation:** one motivated gaze and one low-amplitude physical cue, such as a quiet breath, a brief hold, or lips parting before speech.
2. **Delivery:** one broad intention and emotional temperature for the complete line. Let the audio reference and generated speech carry phonemes and lip timing.
3. **Residue:** one short visible state after the line, such as held eye contact, a softened breath, listening, waiting, or attention returning to the other character.

Use a stable close-up or medium close-up when speech naturalness is the shot's main goal. Keep the complete face inside a safe frame throughout the line, choose one motivated gaze target, and keep camera movement quiet enough to read the performance.

Limit the motion budget. One or two subtle facial or body channels per beat are usually enough. Direct the whole line rather than assigning a different facial action to each word. Prefer observable actions such as a held gaze, a small swallow, breath release, or slight jaw tension over abstract emotion labels.

## Control Levels

### `simple`

Use a concise whole-line intention when dialogue is incidental, the face is small, or the shot is driven mainly by action.

### `light`

Default for visible dialogue. Include preparation, whole-line delivery, and residue or listening.

### `directed`

Use when the line contains a story-visible emotional turn. Add only the few timed changes needed to show that turn. Keep the number of facial beats below the number of spoken clauses whenever practical.

### `experimental`

Use explicit facial-action systems, dense time schedules, or word-level choreography only for an authorized controlled test or a shot whose purpose requires that precision. Record it as an experiment and evaluate it against a simpler baseline before treating it as reusable guidance.

## Audio And Identity

- Bind an approved voice reference to the same speaker and visible character identity.
- State the exact spoken line once.
- Use prompt text for acting, gaze, action order and sound context; use the audio reference for voice identity.
- Keep dialogue, ambience and motivated effects distinct in the `AUDIO` block.

## Escalation

Generate and review the normal `light` version first. If it passes, continue the project. If it fails, identify the strongest cause hypothesis before changing the prompt. Use a controlled A/B comparison only when the cause remains unclear, a new reusable rule needs evidence, or the user explicitly requests the comparison.
