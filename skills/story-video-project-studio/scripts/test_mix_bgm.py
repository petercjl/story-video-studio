import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mix_bgm import main, probe, sha256


def make_film(path: Path) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=blue:s=320x480:r=24:d=3",
        "-f", "lavfi", "-i", "sine=frequency=700:sample_rate=48000:duration=3", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ], check=True)


def make_bgm(path: Path) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
        "sine=frequency=220:sample_rate=48000:duration=3", "-c:a", "pcm_s16le", str(path),
    ], check=True)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class MixBgmTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.film, self.bgm = self.root / "film.mp4", self.root / "bgm.wav"
        make_film(self.film)
        make_bgm(self.bgm)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def plan(self) -> Path:
        path = self.root / "plan.json"
        path.write_text(json.dumps({
            "schema": "story-video-final-mix-plan", "schema_version": "1.0.0",
            "film": {"path": str(self.film), "sha256": sha256(self.film)},
            "bgm": {"path": str(self.bgm), "sha256": sha256(self.bgm)},
            "placement": {"film_start_seconds": 0.5, "bgm_source_in_seconds": 0, "bgm_source_out_seconds": 2.5},
            "mix": {"sample_rate": 48000, "bgm_normalize_lufs": -24, "bgm_base_gain_db": 0,
                    "fade_in_seconds": 0.2, "fade_out_seconds": 0.4,
                    "gain_windows": [{"start_seconds": 1, "end_seconds": 2, "gain_db": -6}],
                    "final_target_lufs": -16, "final_true_peak_dbtp": -1.5},
        }), encoding="utf-8")
        return path

    def test_mix_preserves_video_frames_and_writes_manifest(self) -> None:
        output, manifest = self.root / "mixed.mp4", self.root / "manifest.json"
        self.assertEqual(main(["--plan", str(self.plan()), "--output", str(output), "--manifest", str(manifest)]), 0)
        self.assertEqual(probe(output)["video"]["frames"], probe(self.film)["video"]["frames"])
        data = json.loads(manifest.read_text())
        self.assertEqual(data["original_sound_policy"], "preserve accepted film soundtrack as primary; mix BGM underneath")
        self.assertEqual(data["output"]["loudness"]["status"], "measured")

    def test_rejects_changed_bgm(self) -> None:
        plan = self.plan()
        self.bgm.write_bytes(self.bgm.read_bytes() + b"changed")
        self.assertEqual(main(["--plan", str(plan), "--output", str(self.root / "x.mp4"),
                               "--manifest", str(self.root / "x.json")]), 2)


if __name__ == "__main__":
    unittest.main()
