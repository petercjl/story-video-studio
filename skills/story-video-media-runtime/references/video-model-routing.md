# Video Model Routing

Policy ID: `story-video-seedance-route-2026-09-21`

Evaluate in this order:

1. Preserve an explicit user-selected model after validating its limits.
2. A request above 15 seconds selects Seedance 2.5. A simultaneous 1080p request is unsupported because this route has no verified model satisfying both constraints.
3. Audio-only generation, a request known to exceed Seedance 2.0 reference limits, or an explicit Seedance 2.5 task selects 2.5.
4. A 1080p request selects 2.0.
5. Video editing selects 2.0 for the currently observed spatial-fidelity advantage.
6. Extension, timestamped segment control, or spoken performance selects 2.5.
7. An explicit multi-shot continuity prompt selects 2.0.
8. Ordinary generation falls back to 2.5.

Codex keeps `model=auto` and treats the current `seedancecli` dry-run as the effective route decision. SealSeek maps `seedance-2.0` and `seedance-2.5` through its adapter aliases. Record the policy, reason, detected signals, semantic family and effective native model for every attempt.
