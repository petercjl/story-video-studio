from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

import video_project as project


class ProjectStateTest(unittest.TestCase):
    @staticmethod
    def segment(status: str = "confirmed") -> dict:
        return {
            "title": "Opening", "target_seconds": 15, "status": status,
            "story_file": "story/S01.md", "start_state": "At the door",
            "end_state": "Inside the room", "handoff_out": "Looks toward the window",
            "visible_beats": ["Opens the door and enters the room."],
            "director_brief": "Show the person entering and turning toward the window.",
        }

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = (Path(self.temp.name) / "movie").resolve()
        result = project.main(["init", "--project-dir", str(self.root), "--name", "Test", "--idea", "A story idea"])
        self.assertEqual(result, 0)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_init_preserves_existing_project_and_renders_plan(self) -> None:
        self.assertTrue((self.root / "VIDEO-PLAN.md").is_file())
        self.assertEqual(project.main(["init", "--project-dir", str(self.root), "--name", "Again", "--idea", "Other"]), 2)
        self.assertIn("A story idea", (self.root / "VIDEO-PLAN.md").read_text())

    def test_story_segment_and_impact(self) -> None:
        story_text = "A complete approved story"
        (self.root / "story" / "checkpoint.json").write_text(json.dumps({"schema": "story-development", "schema_version": 1, "story_text": story_text, "duration": {"status": "approved", "approved_seconds": 44}, "review": {"status": "approved", "story_sha256": hashlib.sha256(story_text.encode("utf-8")).hexdigest()}}), encoding="utf-8")
        self.assertEqual(project.main(["story", "--project-dir", str(self.root), "--file", "story/checkpoint.json", "--goal", "Complete the approved 44-second story"]), 0)
        self.assertEqual(project.read(self.root)["settings"]["total_seconds"], 44)
        self.assertEqual(project.read(self.root)["settings"]["goal"], "Complete the approved 44-second story")
        self.assertIn("故事建议时长：44 秒", (self.root / "VIDEO-PLAN.md").read_text())
        self.assertIn("故事：已批准", (self.root / "VIDEO-PLAN.md").read_text())
        self.assertNotIn("创意：A story idea", (self.root / "VIDEO-PLAN.md").read_text())
        (self.root / "story" / "S01.md").write_text("A segment", encoding="utf-8")
        record = self.root / "source" / "segment.json"
        record.write_text(json.dumps(self.segment()), encoding="utf-8")
        self.assertEqual(project.main(["record", "--project-dir", str(self.root), "--kind", "segment", "--id", "S01", "--data-file", str(record)]), 0)
        self.assertEqual(project.main(["impact", "--project-dir", str(self.root), "--source", "segment:S01", "--reason", "Story changed"]), 0)
        data = project.read(self.root)
        self.assertEqual(data["segments"]["S01"]["status"], "confirmed")
        self.assertEqual(data["segments"]["S01"]["review_status"], "needs_review")
        self.assertTrue(list((self.root / "logs" / "history").glob("*video-project.json")))

    def test_story_rejects_stale_approval_hash(self) -> None:
        (self.root / "story" / "checkpoint.json").write_text(json.dumps({"schema": "story-development", "schema_version": 1, "story_text": "Changed story", "duration": {"status": "approved", "approved_seconds": 30}, "review": {"status": "approved", "story_sha256": "0" * 64}}), encoding="utf-8")
        self.assertEqual(project.main(["story", "--project-dir", str(self.root), "--file", "story/checkpoint.json"]), 2)

    def test_missing_accepted_video_fails_complete_gate(self) -> None:
        (self.root / "story" / "S01.md").write_text("A segment", encoding="utf-8")
        record = self.root / "source" / "segment.json"
        record.write_text(json.dumps(self.segment()), encoding="utf-8")
        project.main(["record", "--project-dir", str(self.root), "--kind", "segment", "--id", "S01", "--data-file", str(record)])
        self.assertFalse(project.cmd_validate(type("Args", (), {"project_dir": self.root, "require_complete": True})())["ok"])
        self.assertEqual(project.main(["node", "--project-dir", str(self.root), "--name", "delivery", "--status", "confirmed"]), 2)

    def test_segment_rejects_string_beats_before_state_write(self) -> None:
        (self.root / "story" / "S01.md").write_text("A segment", encoding="utf-8")
        record = self.root / "source" / "segment.json"
        invalid = self.segment()
        invalid["visible_beats"] = "Opens the door"
        record.write_text(json.dumps(invalid), encoding="utf-8")
        self.assertEqual(project.main(["record", "--project-dir", str(self.root), "--kind", "segment", "--id", "S01", "--data-file", str(record)]), 2)
        self.assertNotIn("S01", project.read(self.root)["segments"])

    def test_trimmed_video_requires_source_window(self) -> None:
        (self.root / "story" / "S01.md").write_text("A segment", encoding="utf-8")
        record = self.root / "source" / "segment.json"
        record.write_text(json.dumps(self.segment()), encoding="utf-8")
        self.assertEqual(project.main(["record", "--project-dir", str(self.root), "--kind", "segment", "--id", "S01", "--data-file", str(record)]), 0)
        raw = self.root / "videos" / "raw.mp4"
        raw.write_bytes(b"test video bytes")
        output = self.root / "videos" / "delivery.mp4"
        output.write_bytes(b"short clip bytes")
        video = {
            "status": "accepted", "segment_id": "S01", "task_id": "task-1",
            "request_hash": "hash-1", "output": "videos/delivery.mp4",
            "qa": {"status": "pass"}, "download_duration_seconds": 15,
            "delivery_duration_seconds": 12, "provider_raw": "videos/raw.mp4",
            "provider_raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        }
        record.write_text(json.dumps(video), encoding="utf-8")
        self.assertEqual(project.main(["record", "--project-dir", str(self.root), "--kind", "video", "--id", "V01", "--data-file", str(record)]), 2)
        video["delivery_source_window_seconds"] = [3, 15]
        record.write_text(json.dumps(video), encoding="utf-8")
        self.assertEqual(project.main(["record", "--project-dir", str(self.root), "--kind", "video", "--id", "V01", "--data-file", str(record)]), 0)
        result = project.cmd_validate(type("Args", (), {"project_dir": self.root, "require_complete": True})())
        self.assertTrue(result["ok"], result["errors"])


if __name__ == "__main__":
    unittest.main()
