# Video QA Report Contract

## Required Structure

```markdown
# Video QA: [file or project]

## Overall Result
- Verdict:
- Release blockers:
- Main uncertainty:

## Derived QA Contract
| Criterion | Expected | Modality | Depth | Reference | Verdict |

## Findings
### [Finding]
- Expected:
- Observed:
- Evidence time:
- Severity:
- Confidence:
- Evidence inspected:
- Cause hypothesis:
- Next verification or change:

## Coverage
- Duration:
- Metadata checked:
- Frames inspected:
- Sampling strategy:
- Dense intervals:
- Original-detail views:
- Audio/OCR/ASR/reference comparison:
- Uncovered areas:

## Next Experiment
```

## Verdict Vocabulary

- `pass`: sufficient evidence supports the criterion across its required scope.
- `fail`: evidence shows the criterion is violated.
- `partial`: some required states pass and others fail.
- `uncertain`: evidence exists but cannot support a reliable decision.
- `not_tested`: the modality or criterion was deliberately outside scope.
- `not_verifiable`: required ground truth or reference was missing.
- `human_review_required`: a subjective perception requires human seeing or listening unavailable to the runtime.

## Severity

- `blocker`: invalidates the intended use or experiment.
- `major`: materially harms story, identity, product truth, continuity, or delivery.
- `minor`: visible issue that does not break the primary purpose.
- `note`: observation or successful constraint useful for the next loop.

## Evidence Language

State facts narrowly. Prefer “the daughter presents older than the requested 26-29 screen impression in the close-up at 13.8s” over “the model ignored age.” The latter is a causal hypothesis.

Do not say “watched the whole video” when the runtime inspected sampled frames. Report the actual sampling strategy. Do not call an ASR transcript proof of accent, emotion, or voice appeal.

Record successful constraints as well as failures. They are invariants for the next experiment.

## Optional JSON Record

For A/B loops, emit a parallel JSON object with:

```json
{
  "video": "...",
  "goal": "...",
  "criteria": [],
  "findings": [],
  "coverage": {},
  "generation_provenance": {},
  "next_experiment": {}
}
```
