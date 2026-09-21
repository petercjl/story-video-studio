# Dependency Contract

Resolve dependencies by exact Skill name from the host's advertised catalog or configured Skill roots. Load the callee's complete current `SKILL.md`; never copy its operating instructions into this caller or substitute a similarly named Skill.

| Exact name | Requirement | Handoff | Failure | Return point |
| --- | --- | --- | --- | --- |
| `story-development-director` | Required `story-development@1` contract | story idea → approved `story-development.json` plus story hash | `CAPABILITY_UNAVAILABLE` before segment planning | Main line step 3 |
| `higgsfield-seedance-prompt` | Required two-pass prompt contract | approved segment → draft prompt and `ai-video-reference-asset-request@1.x`; approved assets → final prompt/input map | stop the affected segment before asset generation or video submission | Main line step 4 or 6 |
| `ai-video-reference-asset-studio` | Required `ai-video-reference-asset-package@1.4.x` contract | reference request → approved packages and binding patch | preserve independent assets; block only consumers of missing/failed assets | Main line step 6 |
| `story-video-media-runtime` | Required `story-video-media-request@1.x` and result contract | platform-neutral image/video request → normalized local artifact and evidence | preserve request and return the exact capability/feature error | Main line step 5 or 7 |
| `goal-driven-video-qa` | Optional for demanding quality decisions | generated clip plus quality goals → evidence-backed QA result | continue with ordinary visible review and state the reduced QA depth | Main line step 8 |
| `seedaudiocli` | Required only for BGM/final-mix completion | accepted picture edit and cue prompt → immutable music source | mark final-mix node partial and resume after installation | Main line step 10 |

`topazlabscli` is not part of the current main line. Installing it later does not change delivery resolution automatically; add that branch only through a separately reviewed Skill update.
