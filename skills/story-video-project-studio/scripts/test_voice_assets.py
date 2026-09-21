from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import video_project as project
import voice_assets


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required")
class VoiceAssetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        self.assertEqual(project.main(["init", "--project-dir", str(self.root), "--name", "Voice test", "--idea", "Test"]), 0)
        story = self.root / "story" / "S01.md"
        story.write_text("A speaker talks.", encoding="utf-8")
        record = self.root / "source" / "segment.json"
        record.write_text(json.dumps({"status": "confirmed", "title": "Speech", "target_seconds": 2, "story_file": "story/S01.md", "start_state": "Speaking", "end_state": "Finished", "handoff_out": "Continue", "director_brief": "One line", "visible_beats": ["A sailor speaks."]}), encoding="utf-8")
        self.assertEqual(project.main(["record", "--project-dir", str(self.root), "--kind", "segment", "--id", "S01", "--data-file", str(record)]), 0)
        video = self.root / "videos" / "sample.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=black:s=320x180:r=24:d=2", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(video)], check=True)
        record.write_text(json.dumps({"status": "accepted", "segment_id": "S01", "task_id": "task-1", "request_hash": "hash-1", "output": "videos/sample.mp4", "qa": {"status": "pass"}, "downloaded_duration_seconds": 2, "delivery_duration_seconds": 2, "provider_raw": "videos/sample.mp4", "provider_raw_sha256": hashlib.sha256(video.read_bytes()).hexdigest()}), encoding="utf-8")
        self.assertEqual(project.main(["record", "--project-dir", str(self.root), "--kind", "video", "--id", "V01", "--data-file", str(record)]), 0)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def args(self, **overrides: object) -> argparse.Namespace:
        values = {"project_dir": self.root, "video_id": "V01", "person_id": "C02", "start": 0.2, "end": 1.6, "transcript": "A line", "approval_note": "User approved this speaker voice", "quality_note": "Test tone", "version": 1}
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_extract_register_and_validate(self) -> None:
        result = voice_assets.extract(self.args())
        self.assertEqual(result["voice_id"], "VOICE-C02")
        self.assertAlmostEqual(result["duration_seconds"], 1.4, delta=0.02)
        self.assertTrue((self.root / result["audio"]).is_file())
        self.assertEqual(project.read(self.root)["assets"]["VOICE-C02"]["status"], "approved")
        self.assertEqual(voice_assets.validate(self.root, "VOICE-C02")["sha256"], result["sha256"])
        with self.assertRaises(FileExistsError):
            voice_assets.extract(self.args())
        (self.root / "videos" / "sample.mp4").write_bytes(b"changed source")
        with self.assertRaisesRegex(ValueError, "source video missing or hash mismatch"):
            voice_assets.validate(self.root, "VOICE-C02")

    def test_requires_speaker_approval_before_writing(self) -> None:
        with self.assertRaisesRegex(ValueError, "approval note"):
            voice_assets.extract(self.args(approval_note=""))
        self.assertFalse((self.root / "assets" / "voices").exists())


if __name__ == "__main__":
    unittest.main()
