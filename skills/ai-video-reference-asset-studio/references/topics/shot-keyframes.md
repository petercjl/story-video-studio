# Shot Keyframes

Use this branch only for a formal keyframe task already present in an approved production package or directly specified by the user. Do not design a new shot or multiply the number of frames during generation.

## Authority split

- The upstream shot and keyframe task define the narrative moment, aspect ratio, required state, and acceptance checks.
- The pencil storyboard is `composition` authority: shot size, camera angle, subject placement, screen direction, major overlap, action silhouette, and broad spatial relationship.
- Approved character roots are `identity` authority. Use the original approved identity root, not an angle/state derivative, unless the keyframe task explicitly requires that approved state as a separate visible delta.
- Approved environment masters are `geometry` authority and carry the established scene look.
- Approved prop masters or deterministic panel crops are `structure` or `state` authority. Prefer the crop matching the task's depicted state rather than a whole multi-state board.
- Approved fixed-style text controls photographic register, motivated light, palette, material rendering, contrast, and texture.

The sketch never controls face, wardrobe construction, materials, color, light, photographic finish, or detailed prop identity. Exclude its paper, pencil/ink marks, monochrome rendering, borders, labels, arrows, panel layout, temporary faces, temporary costume, and provisional detail from the finished image.

## Reference order and prompt compilation

Pass the real sketch first, followed by only the approved character, environment, prop/state, and other images that solve a named risk. Keep the fixed style control as text. More references are not inherently better.

Compile the model prompt in this order:

1. standalone photoreal/live-action cinematic-frame instruction and the task's visible narrative moment;
2. composition facts translated from the sketch;
3. concise authority statements for each approved image reference;
4. fixed style core and the environment-matched scene override when present;
5. concise exclusions for storyboard artifacts and identity/structure drift.

Do not paste file paths, IDs, hashes, operator notes, or interface settings into the model prompt. Record them in the package and generation attempt. Record the English prompt exactly as submitted and add a separate Chinese translation for human review; the translation is not the submitted prompt.

## Minimal-frame rule

One upstream keyframe task produces one keyframe candidate by default. Do not infer opening, action, and ending frames merely because a shot contains several states. If the generated video later proves under-controlled, record the observed failure and return `KEYFRAME_COUNT_REVISION_REQUIRED`; only a revised upstream task or explicit user instruction may add another frame.

Do not automatically label the result `first_frame`. A formal keyframe may control an opening state, an action moment, a reveal, or an ending state. Preserve the upstream task's role. A later video-generation adapter decides whether the approved image is uploaded as a general reference or a literal first frame.

## QA

Inspect the real result for:

- composition correspondence without copying storyboard marks or drawing style;
- exact approved character identity, wardrobe, body proportions, and required state;
- environment geometry and light logic;
- prop identity, operational state, orientation, scale, and hand/object contact;
- one coherent finished frame rather than a collage or reference sheet;
- aspect ratio and downstream usability;
- absence of invented people, props, text, logos, and contradictory states.
