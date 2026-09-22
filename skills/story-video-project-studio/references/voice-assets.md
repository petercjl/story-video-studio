# Character voice assets

Read this reference when a segment contains dialogue or when reviewing a newly generated speaking voice. The project `assets` registry is the source of truth for approved voice references.

## Per-speaker lifecycle

1. Before prompting the current segment, list its speaking characters and look up an approved `kind: voice` asset for each `person_id` in `video-project.json`. Match the speaker to the approved character identity or a stable first-appearance ID.
2. For a speaker without an approved voice asset, let the video model generate the voice for that segment. Record the speaking character and exact line in the segment plan. A character who only appears silently has no voice to extract.
3. After generation, identify each speaker's audible time window, listen to the voice, and show the relevant clip to the user. Record whether the user approves **that speaker's voice**. Acceptance of picture or story alone does not automatically approve every voice; clear approval of the complete speaking performance can cover the voices in that clip.
4. For an approved voice, choose a single-speaker excerpt with intelligible speech, record its transcript and source video/time window, and run `scripts/voice_assets.py extract`. The script creates a mono 48 kHz PCM WAV, hashes the source and output, writes an approved package, and registers `VOICE-<person_id>` through `video_project.py`. Keep source ambience and any short-sample limitation in `quality_note`; an extraction from a mixed soundtrack is a voice reference sample, not proof of isolated dry speech.
5. If speech overlaps, the speaker is ambiguous, or the available sample is unsuitable, keep the voice unapproved and seek another generated take or user-provided reference. Preserve prior attempts. If the user rejects a voice, do not register it as an approved asset.
6. On each later segment where that same person speaks, add the approved WAV to the provider input map as a hashed `audios` entry; assign `音频1`, `音频2`, etc. in audio order. State in the prompt which character and dialogue interval each audio tag guides. Match the visual identity and voice `person_id`. A silent appearance does not need that voice input.
7. Dry-run the exact input map and inspect the payload for `reference_audio` entries before real submission. After generation, review audible voice identity, dialogue, lip sync, and speaker assignment against the approved sample. If the provider ignores or confuses a reference, classify it as a video QA failure and use the normal scoped repair path; supplying a reference alone is not a passing result.

## Extraction command

Run only after the user has approved the speaker's voice. Use the current video's saved project ID and the spoken interval in seconds:

```text
story-video-studio run-script story-video-project-studio voice_assets.py extract --project-dir PROJECT --video-id VIDEO_ID --person-id PERSON_ID --start START --end END --transcript "EXACT LINE" --approval-note "USER APPROVAL" --quality-note "SAMPLE QUALITY"
```

Run `story-video-studio run-script story-video-project-studio voice_assets.py validate --project-dir PROJECT --voice-id VOICE-PERSON_ID` before binding. The package supplies `ffmpeg`, checks the source video and hashes, and refuses existing target files. For a replacement voice, use a higher `--version`; retain previous approved versions and update only affected consumers through project impact review.

## Audio entries in the provider input map

`audios` is optional. Include one entry for every speaking character with an approved voice asset. Each entry has `index`, `provider_tag`, `asset_id`, `person_id`, `path`, `sha256`, `package`, and `package_sha256`. Paths are relative to the input-map file. The voice package records the same `person_id`, output path/hash, source video ID/hash, time window, transcript, and user approval. The provider prompt uses the matching `音频N` tag. The current `seedancecli generate input-map` validates order, hashes, package approval, and speaker identity, then submits the files as `reference_audio` content.

When the current provider cannot accept audio references, report `FEATURE_UNSUPPORTED` for voice-conditioned video generation. Keep the segment ready for a capable provider or an explicitly approved audio-postproduction route; do not represent an unconditioned take as voice-consistent.
