# Story development handoff

Use one UTF-8 JSON object:

```json
{
  "schema": "story-development",
  "schema_version": 1,
  "story_id": "day-01-homecoming",
  "title": "I am home",
  "premise": "One concise source premise.",
  "story_text": "The complete approved prose story.",
  "emotional_intent": "What the audience should recognize and feel.",
  "opening_question": "The concrete question created by the opening action.",
  "visible_events": [
    "Complete visible or audible event sentence in narrative order."
  ],
  "continuity_facts": [
    "Confirmed recurring fact stated positively."
  ],
  "logic_decisions": [
    {
      "topic": "sound source",
      "decision": "The cat makes the sound after hearing the door.",
      "reason": "The event has a visible, believable cause."
    }
  ],
  "dialogue": [
    {
      "speaker": "protagonist",
      "mode": "inner_voice",
      "text": "A line spoken in the story."
    }
  ],
  "duration": {
    "status": "deferred",
    "requested_seconds": null,
    "natural_range_seconds": [35, 50],
    "approved_seconds": null,
    "basis": "Visible actions, spoken words, pauses, and transitions."
  },
  "unresolved": [],
  "review": {
    "status": "draft",
    "approved_at": null,
    "story_sha256": null
  }
}
```

## Required behavior

- `visible_events` is ordered and contains complete action sentences.
- `continuity_facts` contains only confirmed facts needed downstream.
- `dialogue.mode` is one of `spoken`, `inner_voice`, `narration`, or `on_screen_text`.
- Duration status is `deferred`, `estimated`, or `approved`.
- `approved_seconds` is required only for `approved` duration.
- `review.story_sha256` is the SHA-256 of the exact UTF-8 `story_text` when approved.
- A changed story invalidates prior approval until `approve` is run again.

Validate before handing the file to the segment planner:

```bash
story-video-studio run-script story-development-director story_checkpoint.py validate path/to/story-development.json
story-video-studio run-script story-development-director story_checkpoint.py approve path/to/story-development.json
```

`approve` updates the same file through a temporary file and atomic rename. The caller should preserve project history before approval when its project contract requires versioned recovery points.
