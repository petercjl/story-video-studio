# Spoken Performance QA

Use this contract for a visible speaking character. Inspect the complete beat with synchronized picture and sound at normal playback speed before using frame-level evidence.

## Criteria

| Criterion | Expected state | Evidence |
|---|---|---|
| Voice identity | The audible speaker matches the approved character voice or the current first-voice candidate. | Playback plus approved voice reference when available. |
| Exact line | The intended line occurs once, in the intended order, without material omissions or additions. | Playback and ASR as supporting evidence. |
| Lip timing | Mouth motion begins, continues and settles in plausible relation to the audible speech. | Playback; dense frames around suspected offsets. |
| Articulation | Jaw, lips and cheeks move with restrained variation appropriate to the delivery. | Playback and targeted close inspection. |
| Gaze | The gaze has a motivated target and changes only when the scene gives it a reason. | Whole beat and adjacent listener/action context. |
| Face-safe framing | Eyes, mouth, chin and the intended expression remain readable throughout the line. | Full-frame playback and boundary frames. |
| Preparation | A visible speaking cue precedes the first word when the prompt calls for one. | Short pre-line window. |
| Residue or listening | The face and body retain a motivated state after the line instead of snapping neutral or starting an unrelated action. | Post-line window and stimulus-response order. |
| Identity stability | Face, age impression, hair, wardrobe and body remain continuous through speech. | All appearances during the beat. |
| Naturalness | The combined voice, timing, gaze, expression and body behavior feel like one motivated performance. | Human synchronized viewing and listening. |

Check whether blinks, nods, brows, mouth, cheeks and head movement repeatedly activate together. Treat conspicuous synchronization, repeated gesture loops, excessive articulation, frozen listening, premature reactions and a face leaving the safe frame as candidate failures. Describe the observed behavior and time range; do not infer a model cause without an experiment.

## Verdict Boundary

Metadata, ASR and frame samples cannot establish acting naturalness by themselves. When synchronized perceptual review is unavailable, report measurable findings and mark naturalness `human_review_required`.

## Troubleshooting

If the clip passes, continue the normal project workflow. If it fails, choose the strongest cause hypothesis: voice, lip timing, gaze, framing, performance direction, identity drift, continuity, or random generation variation. Recommend one smallest relevant change.

Use A/B only when the cause is unclear, a reusable prompt rule needs evidence, or the user asks for a comparison. Preserve unrelated settings and record seed availability. Different seeds make the comparison directional rather than conclusive; one project result remains a scoped candidate until reproduced.
