# Controlled Video Experiment Loop

Use this protocol when video QA informs prompt or generation changes.

This is an exception and learning loop, not a mandatory step for every accepted clip. Enter it when a material failure has more than one plausible cause, when a proposed reusable constraint needs evidence, or when the user explicitly requests a comparison. If the baseline passes, retain it and leave the loop.

## Loop

```text
baseline video
-> derive QA contract
-> inspect and record evidence
-> choose strongest cause hypothesis
-> propose smallest relevant change
-> preserve unrelated invariants
-> obtain generation authorization
-> generate candidate
-> inspect candidate with the same QA contract
-> compare A/B
-> retain, reject, or refine the hypothesis
```

## Provenance To Preserve

- prompt file and version or hash;
- model and provider;
- seed when available;
- duration, ratio, resolution, fps, and audio setting;
- reference media and order;
- task id and output file;
- user acceptance or rejection.

## Variable Control

Change one causal variable group when practical. If testing casting, preserve environment, camera, dialogue, model, and delivery settings. If a production constraint forces several changes, list them and state that causal attribution will be weaker.

Preserving a seed strengthens attribution when the provider supports it. When variants use different or unavailable seeds, report the result as directional evidence because random variation may account for part of the difference. Repeat across another run, story, or asset before promoting the result beyond a scoped candidate rule.

Carry successful constraints forward as invariants. Do not rewrite parts that already passed unless they conflict with the new test.

## Constraint Promotion

- One failure: hypothesis or case note.
- Reproduced failure: candidate constraint.
- Effective across different stories or assets: general rule.
- Effective only for one video class: branch rule.
- Project-specific fix: keep outside the shared Skill.

Critical safety or truthfulness rules may enter immediately, but label their evidence and scope.

## Authorization Boundary

QA is read-only. A recommendation is not authorization to edit prompts, alter media, upload references, or spend generation credits. Request or infer authorization only from an explicit generation/change instruction.
