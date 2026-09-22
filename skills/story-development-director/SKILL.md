---
name: story-development-director
description: Develop a short-video story idea into a coherent, emotionally legible story checkpoint and a validated production handoff. Use before segment planning when a premise, fragment, theme, or draft still needs causal, behavioral, spatial, emotional, or duration reasoning.
---

# Story Development Director
## Distribution preflight

Before the first story action in each conversation, run `story-video-studio preflight --agent <codex|sealseek> --node story --json` using the current host identity. If the CLI reports an update, reload this Skill from the exact canonical path returned by preflight before continuing. If preflight fails, return its structured repair instruction.


Turn an idea into an approved story before designing video segments. Preserve the user's central feeling and recognizable life detail while repairing logic that would make the scene feel written or artificial. Story files, rather than conversation memory, carry the approved result forward.

## Input → Strategy → Output

**Input:** a premise, fragment, theme, draft, or collection of story facts; optional character, setting, emotional intent, dialogue, duration, format, and continuity constraints.

**Strategy:** establish what the audience should understand and feel; build a visible cause-and-effect chain; test behavior and physical events against ordinary human experience; refine the story text with the user; then estimate a natural screen duration from the accepted actions and speech.

**Output:** one validated `story-development@1` JSON file containing the approved story text, emotional intent, opening question, visible event chain, continuity facts, logic decisions, duration assessment, approval evidence, and content hash.

## Main line

1. **Frame the story.** Identify the protagonist, immediate situation, audience question, emotional recognition point, change by the end, and facts that must remain fixed. Infer these from supplied material before asking for information already present.
2. **Develop the complete story text.** Write the story as continuous prose that describes what visibly and audibly happens. Give each action a reason, let the character's behavior match the situation, and preserve enough quiet time for the emotional turn to register.
3. **Run the reality pass.** Check everyday behavior, object state, location, time of day, entrances and exits, sound sources, cause and effect, information available to each character, and whether a visual metaphor can be understood on screen. Repair weak links with the smallest change that preserves the intended feeling.
4. **Run the emotional pass.** Confirm that the opening creates a concrete question, the middle reveals the pressure or memory behind the behavior, and the ending changes the meaning of an earlier action. Dialogue or inner voice may clarify an otherwise private feeling, but it should arise from the character's present experience.
5. **Review story content first.** Present the complete story and material logic decisions as one checkpoint. During active story repair, do not force the story into an earlier time estimate. Revise the story until the user approves its content.
6. **Assess screen capacity.** After the story content is stable, estimate a natural duration from visible beats, dialogue or narration, pauses, and transitions. If a requested duration would make the story rushed or padded, explain the mismatch and recommend the natural range. Duration remains `deferred` until discussed and becomes `approved` only with user acceptance.
7. **Build and validate the handoff.** Create `story-development.json` according to [the handoff contract](references/story-development-contract.md). Run `scripts/story_checkpoint.py validate`. When the user approves the story and duration decision, run `approve`; never write approval merely because a draft exists.
8. **Return to the caller.** Provide the JSON path, fingerprint, approved story text, duration status, fixed continuity facts, and unresolved items. The caller may then plan independently generatable video segments.

## Judgment rules

- Prefer a small believable action over explanatory plot machinery.
- Treat household sounds, messages, props, and environmental changes as events with a visible source and timing.
- Distinguish inner voice, spoken dialogue, text on screen, and ambient sound because they require different production assets.
- Preserve ambiguity when it creates feeling; remove ambiguity when it hides basic cause, identity, location, or action.
- A poetic line succeeds only when the preceding event gives it a clear referent.
- Do not introduce additional characters, locations, props, or effects merely to fill time.
- Record confirmed story facts positively. Keep rejected drafts and correction history outside the final handoff unless the project explicitly requires an audit log.

## Branches

- **Fragment without an ending:** propose one or more endings grounded in the established action, then return to story review.
- **Emotion clear, event weak:** find a recognizable behavior that physically expresses the feeling, then return to the reality pass.
- **Event clear, emotion private:** add a motivated look, hesitation, choice, spoken line, or inner voice, then return to the emotional pass.
- **Requested duration too short:** preserve the approved story and recommend either a longer duration or an explicitly reduced event chain; return to content review if events change.
- **Series continuity supplied:** treat recurring character, home, voice, pet, wardrobe, and personality facts as fixed continuity, and expose them in the handoff.
- **Approval pending:** keep `review.status = "draft"` and stop before segment planning.

## Completion gate

Complete only when the story is understandable without production notes; physical and behavioral causes are plausible; the emotional turn is supported by visible or audible events; duration status is honest; the JSON validates; approval evidence matches the current story hash; and unresolved items are explicit.
