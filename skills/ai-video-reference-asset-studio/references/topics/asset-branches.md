# Asset Branches

## Character

Choose the asset form before generation.

For `higgsfield-three-panel`, create one 16:9 horizontal identity sheet on a continuous neutral medium-gray studio backdrop with thin dividers and consistent soft, low, diffused light:

1. left: direct front body-and-wardrobe full view, neck to boots, neutral stance, hands visible; the head and face are cleanly absent, with no blur, placeholder face, mannequin head, wound, or gore;
2. center: direct back full-body view, head to boots, same body and wardrobe; only the back of the head/hat may appear and no facial feature is visible;
3. right: direct frontal close-up from chest upward, eyes toward camera, face readable; this is the sole authority for face, facial identity, and expression.

All panels must depict the same body, wardrobe, proportions, grooming visible from behind, accessories, material wear, and baseline state. The right panel alone defines facial identity. This complete sheet is the root candidate for a new fictional character and becomes the identity root only after user approval. If an approved casting or identity source already exists, use it to construct the sheet while preserving the same panel authority split.

A single portrait/full-body image is permitted only as an explicitly requested calibration checkpoint. It is not a completed Higgsfield character asset and cannot satisfy the identity-sheet deliverable. After the sheet is approved, generate only additional views and states demanded by consumers, each directly from the approved sheet rather than another derivative.

For `derived-character-control`, use the recursively resolved original identity sheet as the image-generation reference. An angle task changes only view/framing/pose. A state task changes only the declared state delta, such as dust, wetness, damage, or wardrobe state. Both preserve the root face, body proportions, wardrobe construction, accessories, materials, and colors. Record the root path and hash in `identity_root`, the identity reference, and every attempt's `input_files`.

Character state assets default to a portrait 9:16 canvas so the complete character, face, state delta, and surrounding silhouette margin remain useful for vertical-video production. This asset-level default applies even when the upstream task omits a ratio or the project-level video ratio is 16:9. An explicit task-level asset ratio may override it. Record the control as `operator_notes.control_type = state`, carry `9:16` through interface parameters and attempt parameters, state the portrait composition in the model prompt, and visually verify the returned canvas ratio.

QA: exact three-panel order and framing; zero visible facial features outside the right panel; right panel as sole face authority; matching front/back body and wardrobe structure; age and role signal; intact hands/feet; neutral usability; continuous background/light; absence of scene action or unrelated props; and clean 16:9 delivery. A visible or blurred face in the left panel fails because a low-detail full-body face can compete with the close-up identity source during video generation.

## Environment

Create an empty master that supports action: stable coordinate frame, entrances, landmarks, action surface, movement path, depth, and dominant light. Compile its look by combining the environment task's own spatial specification, the shared fixed style prompt, and the matching scene override. The environment specification remains authoritative for geometry; the style control remains authoritative only for photographic register, light, palette, material rendering, contrast, and texture. Add another view only when the master or an approved spatial bridge establishes it.

An environment angle or state derivative recursively resolves and uses the original approved environment master. It may change only the requested view, time/light state, weather, dressing state, or damage delta. Do not use another generated angle as the geometry root.

QA: geography, path clearance, landmarks, light direction, empty-scene purity, camera usefulness, and compatibility across views.

## Prop

Create one object or one intentional reference sheet at a time. Lock silhouette, material, scale evidence, functional connections, and story state. When the same prop needs several compatible views or states, prefer one `multi-state-prop-board` so one upstream row maps to one user-facing image.

Order board panels by authority: principal surface first, other required surfaces second, operational or story states last. Keep all panels on one clean continuous studio background, at useful scale, with no decorative text. After approval, crop each panel mechanically and record the crop as an intermediate technical output. Downstream generation selects the crop matching the required surface or state; the master board remains the approved identity and review artifact.

Split into children only when one board cannot provide adequate resolution or a single approval/authority decision. Different objects never share one identity board merely because they appear in the same upstream row.

A prop view or state derivative recursively resolves and uses the original approved prop root. Preserve structure and connections; apply only the declared view or state delta.

QA: identity/structure, scale, side/state, grasp or operation logic, legibility when required, and separation from unrelated objects.

## Style Control

Do not generate an image for `fixed-style-prompt`. Resolve it as a reusable operator input. The fixed core supplies the shared capture language; the environment's matching override supplies local light, color, weather/time, and material state. Reject missing, duplicate, or mismatched environment overrides upstream before generation.

Legacy style images may still be inspected or packaged when a direct, independently approved brief requests them, but they are not required when an approved textual style control is sufficient.
