# Segment handoff continuity

Use this procedure before finalizing and generating every segment after the first. Its input is the immediately preceding **accepted current video**, never merely the preceding script, an older candidate, or a remembered conversation description. Its output is a recorded handoff package and active references for the next segment's opening.

## Required handoff package

Record:

- predecessor segment and accepted video ID;
- local video path, SHA-256, duration and the inspected tail window;
- one last stable frame plus enough earlier frames or a short tail clip to read motion;
- the outgoing state ledger below;
- the next segment's intended opening state;
- `continue` or `deliberate-transition`, with the visible transition named for the latter;
- approved reference package paths and hashes used by the new prompt.

The outgoing state ledger covers only facts visible or audible at the join:

1. **Space:** location, ship/room/terrain geometry, relative distances and scale, approach side, navigable gaps and important obstacles.
2. **Camera axis:** camera side, shot direction, screen direction, eyelines and which target lies along each gesture or movement.
3. **People:** identities present, exact standing/sitting positions, body orientation, pose, gaze, expression and who is entering or leaving.
4. **Action:** last completed action, action still in progress, velocity or inertia, and the first action that remains for the next segment.
5. **Objects and environment:** held props, equipment state, doors/windows/ropes/vehicles, damage, wetness, lighting, weather, fog, tide and sound bed.

## Reference preparation

Inspect the predecessor tail at normal playback speed and around the cut frame. Use the actual accepted source file at native resolution. Prefer a short tail video when the provider accepts video references; otherwise extract stable frames that jointly show the spatial relationship and character blocking. When one frame cannot express both, create separate geography and character-position references.

An extracted frame inherits acceptance only as an unchanged continuity record from the accepted video. Register its exact source video, timestamp and hash. Classify frames containing recognizable people as human references and retain their approved character identity roots. Do not replace the identity root with the extracted frame.

## Prompt and submission gate

Write the new opening as a direct continuation of the handoff ledger. Specify what the reference controls: for example, distance and scale, rail side and standing position, or the direction of a pointing arm. Keep the reference active only for the shots it governs.

Before a paid submission, verify all of the following:

- the predecessor video is the accepted current version;
- the recorded tail window and hashes still match disk;
- the continuity references appear in the final input map and translated provider request;
- the opening prompt names the outgoing state it preserves;
- story progression does not require the prior segment's completed action to repeat;
- any deliberate transition is visible and explains the state change.

If any check fails, stop at the second prompt pass and repair the handoff package or opening design.

## Review gate

Review the predecessor tail and new opening side by side and at playback speed. Fail continuity when the new segment silently resets distance, reverses a route or screen direction, moves a person or object without elapsed action, changes the camera side so identities or destinations become ambiguous, repeats a completed action, or changes the environment without a visible transition.

When only the new opening fails, use the local-shot-repair branch if a replacement can join cleanly. After the user accepts the composite, register that exact composite as the segment's current accepted video. The following segment must build its handoff package from the accepted composite, not from any earlier generation.
