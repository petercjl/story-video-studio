# Background music and final mix

Use this branch after the combined picture edit is accepted. Return to Main Line Step 10 after the mixed complete film is inspected.

## Input and output contract

- **Input:** accepted combined picture edit; its story and assembly timing; original soundtrack; optional approved series music identity.
- **Strategy:** design a cue against the complete film, generate one instrumental master with `seedaudiocli`, then mix it under the accepted soundtrack with deterministic timing and gain automation.
- **Output:** cue plan, separately preserved BGM master and generation record, mix plan, mixed complete-film candidate, mix manifest, QA evidence and one user decision on the complete film.

The BGM master is a production asset, not a standalone review deliverable. Keep it for provenance and reuse, but ask the user to judge music only in the complete film where dialogue, effects, images and pacing are present.

## 1. Design the cue from the locked film

Watch the complete film and mark:

1. scene and emotional turns;
2. dialogue and narration windows;
3. story-bearing sounds such as footsteps, doors, notifications, animal sounds and meaningful silence;
4. the first moment when music should enter;
5. the intended musical release and final resolving frame.

Do not assume wall-to-wall music. Preserve an unscored opening or other silence when natural sound establishes reality, tension or attention. Use a musical entrance, withdrawal or harmonic change to mark a real story-state change.

Write a cue plan before generation. It contains the film path/hash and duration, absolute film timing, protected sound windows, musical role, emotion arc, instrumentation, density, rhythm, entry and ending behavior. For a series, reuse an approved motif or instrumentation identity when continuity is desired; otherwise create an original cue for this film.

## 2. Generate the music master

Resolve exact `seedaudiocli` from the current runtime and read its complete current Skill before use. Prefer text-to-audio for a new cue and WAV at the film's sample rate, normally 48 kHz.

The prompt states:

- precise target duration;
- original instrumental music, with no voice, speech, lyrics, choir or vocal texture;
- the story and emotional movement;
- instruments, density, rhythm and frequency space;
- time-relative musical sections;
- room for dialogue, effects and ambience;
- a complete ending with a controlled tail.

Dry-run the exact request before a paid submission. Save the prompt, request hash and provider task ID immediately. Download the result through the CLI, measure its real duration and preserve the original file. A small length excess may be trimmed at a musical boundary. Regenerate when the cue is materially too short, contains vocal material, misses the story turn or cannot end cleanly without time stretching. Do not use large tempo changes merely to force duration.

## 3. Build the review mix

Preserve the accepted film's original soundtrack as the primary track. Music sits beneath it. Use a versioned JSON plan and run:

```bash
python3 scripts/mix_bgm.py \
  --plan PROJECT/delivery/final-mix-plan-v01.json \
  --output PROJECT/delivery/final-with-bgm-v01.mp4 \
  --manifest PROJECT/delivery/final-mix-manifest-v01.json
```

The plan uses absolute paths or paths relative to its own location and records SHA-256 for both inputs. It defines the music source window, film placement, fades, base level, dialogue/effect ducking windows, output sample rate, integrated loudness target and true-peak ceiling.

Start with the original soundtrack unchanged. Normalize the BGM to a restrained bed, then lower it further during quiet speech and meaningful effects. Use manually reviewed timing as the main control; automatic sidechain compression may be a safety layer but must not pump with notification sounds or room noise. Fade on musical phrases and preserve the last spoken word and room-tone tail.

## 4. Review the complete film

Review only the mixed complete-film candidate with the user. Internally inspect:

- every line remains effortless to understand;
- story-bearing sounds still read clearly;
- the cue enters at the intended state change;
- music supports one emotional arc rather than restarting at segment joins;
- no generated voice, lyric or distracting lead occupies the speech range;
- no abrupt music cut, clipping, pumping or excessive loudness occurs;
- the opening and final silence or tail feel intentional;
- output duration and video frames match the accepted picture edit.

Preserve the picture edit, BGM master, cue plan, generation record, mix plan, manifest and every prior mixed candidate. When the user rejects the complete film, diagnose whether to change the music prompt, cue timing or mix automation, create a new version and return to this review step.

## Completion

The final mixed film becomes approved only after user review. A technically valid BGM file or mix render alone does not complete delivery.
