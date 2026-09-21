# Prompt And QA Contract

Every request has an operator layer and a model prompt.

The operator layer contains asset/source IDs, purpose, consumers, references and roles, interface parameters, dependencies/waivers, observable checks, and approval requirement.

The model prompt contains only visible content, view/framing, pose/state, spatial relationships, light, material, style, and concise reference locks. Existing references carry visible identity and structure; do not reconstruct them as a parts list. Model and interface parameters stay outside the prompt.

For a no-reference fictional character, define only story-required distinctions. For a reference-based asset, state that visible identity, structure, proportion, material, color, and relationships follow the approved reference, then describe only the requested view/state.

For a same-kind derivative, the operator layer records the recursively resolved root task, exact file, SHA-256, package source, and role. The model prompt refers to the approved reference as the source of truth and describes only the requested angle or state delta. Pass the resolved root file to the generation capability. QA compares the output against both the root and the requested delta; an attempt whose `input_files` omits the root is invalid even when the image looks plausible.

For a character state derivative, the operator layer records `control_type = state` and a default `aspect_ratio = 9:16`; the project-wide video ratio is not an asset-size instruction. The model prompt explicitly asks for one portrait 9:16 state reference with the complete character and readable face/state delta. The selected attempt records `requested_aspect_ratio = 9:16`, and QA checks the real returned pixel ratio. Use another ratio only when the selected task itself explicitly declares an asset ratio.

For `higgsfield-three-panel`, the model prompt must explicitly state the horizontal 16:9 sheet, continuous neutral medium-gray background, consistent low diffused light, thin panel separation, exact left/center/right duties, and same-body/same-wardrobe invariants. The left panel must cleanly omit the head and face rather than blur or replace them; the center must face directly away; the right frontal close-up must be named as the sole facial authority. The operator layer records `asset_form`, panel roles, aspect ratio, and exclusive face authority separately. QA must inspect each panel and fail any visible facial feature outside the right panel; a visually good single portrait or a three-panel sheet with two face sources is an automatic profile failure.

For an environment with `style_controls`, compile the model prompt in this order: the selected environment's visible spatial specification, the fixed `prompt_core`, then the unique matching `scene_override.prompt`. Resolve overlap in favor of the environment specification for geometry and in favor of the style control for photographic register, motivated light, palette, material rendering, contrast, and texture. Remove repeated wording and do not introduce named characters, plot action, or geometry from the style control. The operator layer records the source style task and authority separately. QA checks both scene-specific geography and the inherited style dimensions.

Legacy `style-reference-frame` and `multi-panel-style-board` requests keep their recorded contracts when explicitly selected from a compatible historical package; they do not become a prerequisite for current environment generation.

For `shot-keyframe`, keep composition and appearance authority separate. Translate the pencil sketch into framing, angle, blocking, screen direction, overlap, action silhouette, and broad spatial relations. Approved image assets supply identity, wardrobe, geometry, object structure/state, materials, and established light; fixed style text supplies photographic finish. The submitted prompt must request one standalone finished cinematic still and exclude storyboard paper, pencil/ink marks, monochrome treatment, borders, labels, arrows, grids, and temporary drawn identity. Record the English prompt exactly as sent and provide a separate Chinese translation for review.

`technical_result` is `pass`, `fail`, or `needs-review`. `user_approval` is `pending`, `approved`, or `rejected` and cannot be inferred from technical success. Only approved assets enter downstream bindings.
