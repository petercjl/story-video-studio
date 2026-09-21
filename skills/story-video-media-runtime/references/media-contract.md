# Media Request And Result Contract

## Request

```json
{
  "schema": "story-video-media-request",
  "schema_version": "1.0.0",
  "request_id": "segment-S01-attempt-01",
  "media_kind": "image-or-video",
  "prompt": "effective prompt",
  "references": [{"role":"character-or-environment-or-prop-or-first-frame-or-last-frame-or-audio","uri":"approved local path or URL","asset_id":"optional stable ID","sha256":"required for a local approved source","approval":"approved"}],
  "delivery": {"aspect_ratio":"9:16","resolution":"2K-or-720p","duration_seconds":10,"output_path":"new project-relative path"},
  "routing": {"explicit_model":null,"task_type":"generate","audio_only":false,"exceeds_2_0_reference_limits":false,"timestamped_segments":false,"spoken_performance":false,"multi_shot_continuity":false},
  "authorization": {"paid_generation":true,"scope":"one candidate or named clip batch"}
}
```

An image caller may omit duration and routing. A video caller supplies every known signal. Reference order is significant.

## Result

```json
{
  "schema":"story-video-media-result",
  "schema_version":"1.0.0",
  "ok":true,
  "request_id":"segment-S01-attempt-01",
  "platform":"codex-or-sealseek-openclaw",
  "adapter_schema_version":"1.0.0",
  "route":{"selected_family":"seedance-2.0-or-seedance-2.5-or-null","selected_model":"effective native model or null","policy":"policy identifier","reason":"short reason","signals":[]},
  "task_id":null,
  "artifacts":[{"remote_url":"provider URL when present","local_path":"project-relative path","sha256":"hex digest","bytes":1,"content_type":"image/png-or-video/mp4"}],
  "metadata":{"provider":null,"native_request_hash":null},
  "cost":{"amount":null,"unit":null,"raw":null},
  "warnings":[]
}
```

Failures keep the same envelope with `ok: false`, `error.code`, `error.message`, `error.capability`, and `error.required_feature` when relevant.
