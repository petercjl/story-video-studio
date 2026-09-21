#!/usr/bin/env python3
"""Media-level regression tests for exact-frame local repair."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from replace_video_shot import audio_hash, media, replace


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class ReplaceVideoShotTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        root = Path(self.folder.name)
        self.source = root / "source.mp4"
        self.candidate = root / "candidate.mp4"
        self.output = root / "joined.mp4"
        self.manifest = root / "joined.json"
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red:s=96x64:r=24:d=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-c:v", "libx264",
            "-c:a", "aac", "-shortest", str(self.source),
        ], check=True)
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=96x64:r=24:d=0.5",
            "-c:v", "libx264", str(self.candidate),
        ], check=True)

    def tearDown(self):
        self.folder.cleanup()

    def test_exact_frames_and_original_sound(self):
        report = replace(self.source, self.candidate, 6, 12, 3, self.output, self.manifest)
        self.assertEqual(report["source_window_frames"], [6, 12])
        self.assertEqual(report["replacement_window_frames"], [3, 9])
        self.assertEqual(media(self.output)["frames"], media(self.source)["frames"])
        self.assertEqual(audio_hash(self.output), audio_hash(self.source))
        self.assertTrue(self.manifest.is_file())

    def test_refuses_short_candidate_and_existing_output(self):
        with self.assertRaises(ValueError):
            replace(self.source, self.candidate, 6, 18, 3, self.output)
        self.assertFalse(self.output.exists())
        self.output.write_bytes(b"user-owned")
        with self.assertRaises(FileExistsError):
            replace(self.source, self.candidate, 6, 12, 3, self.output)
        self.assertEqual(self.output.read_bytes(), b"user-owned")


if __name__ == "__main__":
    unittest.main()
