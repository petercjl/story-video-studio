# Goal Routing And Inspection Depth

Use this reference to translate a natural-language QA goal into modalities and evidence.

## Routing Matrix

| Goal | Required evidence | Typical escalation |
| --- | --- | --- |
| Resolution, ratio, duration, fps, codec | `ffprobe` metadata | Decode check when corruption is suspected |
| Unwanted subtitles, text, watermark | Full-duration visual scan; optional OCR | Higher-frequency scan around short overlays |
| Character age or casting impression | Every useful face view at original detail | Close-ups, multiple angles, first/last identity comparison |
| Character identity consistency | All appearances, shot boundaries, face/body/style states | Dense frames around cuts and re-entries |
| Product/reference consistency | Actual references plus every product appearance | Crops of structure, markings, hand interaction, state changes |
| Action realism or deformation | Adjacent frames across the full action | 0.1-0.5 second dense window or frame-level inspection |
| Spatial continuity | Establishing frames, side/zone ledger, cut pairs | Dense inspection around crossings and reverse angles |
| Story/prompt adherence | Prompt/script/shot list plus representative and target frames | Inspect every referenced beat and missing beat interval |
| Pacing or hook | Full timeline, cut rhythm, first 3/15/30 seconds | Scene/cut map and continuous playback when available |
| Dialogue correctness | Audio extraction plus ASR and script comparison | Word-level timing and speaker separation |
| Accent, timbre, acting, emotional truth | Perceptual listening by capable runtime or human | Preserve clips and request human listening |
| Audio quality or sync | Audio stream, waveform/loudness, A/V landmarks | Sample-accurate or frame-accurate sync inspection |

## Choosing Depth

Use `quick` only when the target is deterministic and local, such as checking 1280x720 output or confirming an audio stream exists.

Use `standard` for broad content review. Cover the whole duration with scene-aware or uniform samples, then inspect target evidence at native detail.

Use `deep` for identity, product fidelity, casting, continuity, text that may flash briefly, or failures that sparse sampling can miss.

Use `forensic` for transient anatomy faults, exact A/V sync, corruption, duplicate/missing frames, frame-specific compositing errors, or disputed conclusions.

## Automatic Escalation Triggers

Escalate locally when:

- the target is visible in only a few frames;
- the first and last appearances disagree;
- a contact sheet suggests but cannot prove a failure;
- user feedback contradicts the first review;
- OCR or ASR confidence is weak;
- a cut, occlusion, fast motion, steam, blur, or lighting change can hide the issue;
- the criterion is release-blocking.

Do not automatically extract audio, run OCR, or inspect every frame when the target does not require it.

## Contact Sheet Readability

Treat a contact sheet as navigation and coverage evidence, not as sufficient proof for faces, product details, or transient faults. Choose columns from the task rather than imposing one universal layout: 4-6 columns usually preserve useful detail for casting, environment, and composition; 8-12 columns can summarize dense subtitle or motion scans. Open decisive frames at original resolution before issuing a semantic verdict.
