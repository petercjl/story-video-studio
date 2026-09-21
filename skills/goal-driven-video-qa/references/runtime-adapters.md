# Runtime Capability Adapters

The core workflow requires capabilities, not fixed Agent tool names.

## Required Capability Map

| Capability | Preferred local implementation | Fallback | Honest limitation |
| --- | --- | --- | --- |
| Command execution | Run bundled script and system CLIs | User runs commands | No deterministic evidence package |
| Metadata probe | `ffprobe` | Media inspector with equivalent fields | Technical criteria may be unverified |
| Frame/audio extraction | `ffmpeg` | Equivalent decoder | Sampling options may differ |
| Image perception | Runtime image viewer with original-detail support | Export frames for user review | Semantic visual criteria require human review |
| Continuous motion perception | Native video playback or dense frame sequence | Sub-second frame extraction | Rhythm and micro-motion confidence is lower |
| Speech content | Local ASR | User transcript | Words or timing may be unverified |
| Subjective audio perception | Runtime audio playback/listening or human | ASR plus technical audio checks | Accent, timbre, acting, and emotional truth remain human-review items |
| OCR | Local OCR or visual inspection | Dense exported frames | Short text may be missed |

## Privacy

Prefer local processing. Do not upload a private video, human reference, voice, or extracted media to an external service without authorization. Local evidence directories may contain sensitive frames or audio; place them in a task-scoped location and report them to the user.

## Output Contract

Adapters do not change the report vocabulary or coverage requirements. If a capability is missing, mark the affected criterion `not_tested`, `not_verifiable`, or `human_review_required`; never silently degrade to a pass.
