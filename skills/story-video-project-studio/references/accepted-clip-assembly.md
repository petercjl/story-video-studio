# Accepted-clip assembly

Use this branch after every planned segment has an accepted current video and the user requests one combined film. Return to Main Line Step 9 after the candidate and its joins are reviewed.

## Input and output contract

- **Input:** `video-project.json`; every segment's accepted `current_video_id`; optional reviewed frame trims.
- **Strategy:** establish a direct-cut baseline, judge each adjacent handoff, trim only complete redundant material, then build deterministically.
- **Output:** an assembly plan, combined candidate, manifest, join sheets, project attachments and a separate user decision for the combined film.

Run:

```bash
story-video-studio run-script story-video-project-studio assemble_accepted_videos.py plan \
  --project-dir PROJECT \
  --output-plan PROJECT/delivery/assembly-plan-v01.json

story-video-studio run-script story-video-project-studio assemble_accepted_videos.py build \
  --project-dir PROJECT \
  --plan PROJECT/delivery/assembly-plan-v01.json \
  --output PROJECT/delivery/combined-v01.mp4 \
  --manifest PROJECT/delivery/assembly-manifest-v01.json \
  --qa-dir PROJECT/delivery/qa-v01
```

The script refuses missing, changed, non-current or non-accepted sources. It normalizes video and audio in one render, preserves source clips, and creates a four-frame sheet around every join.

## Join review method

1. Generate the default plan with full source windows and build a direct hard-cut baseline.
2. For every join, watch the prior ending and next opening together. Also inspect the join sheet and the source shots around both sides.
3. Keep the direct cut when location, character state, action direction, screen direction, light, sound and pace form a readable continuation.
4. Move the **next clip's in-point** when its opening repeats an action already completed, repeats an establishing shot, contains setup that no longer serves the combined film, starts before the intended reaction, or adds a dead pause. Select the first frame of the first complete usable shot. Keep enough anticipation for the action to read and retain any needed dialogue onset or sound cue.
5. Move the **prior clip's out-point** only when its own ending contains a redundant hold, repeated action, freeze artifact or material that contradicts the next state. Do not cut merely to make every segment shorter.
6. Prefer hard cuts. A dissolve can hide a weak join while creating double images and muddying time. Use an overlap, J-cut, L-cut or designed transition only as a separately reviewed audio or editorial change; the base script does not invent one.
7. Rebuild into a new version after each plan change. Inspect the complete candidate, every join at playback speed, dialogue integrity, audio level changes, the opening and final frame. Ask the user to approve the combined film separately.

## Decision limits

- Do not trim within a spoken word, a required reaction, a contact action or a camera move unless the remaining motion is still continuous.
- Do not choose cuts from duration alone. Story state and complete shot boundaries decide the edit.
- Do not use an unaccepted candidate merely because it joins better. Return to video QA if no accepted source can make a coherent handoff.
- Preserve the source videos and earlier combined candidates. Every new attempt receives a new plan, output and manifest path.
