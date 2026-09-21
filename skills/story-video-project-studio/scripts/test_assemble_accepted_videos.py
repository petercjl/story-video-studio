import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from assemble_accepted_videos import main, probe, sha256


def make_clip(path: Path, color: str) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"color={color}:s=320x480:r=24:d=1",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(path),
    ], check=True)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg/ffprobe required")
class AssembleAcceptedVideosTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_plan_and_build_with_next_clip_head_trim(self) -> None:
        project = self.root / "project"
        videos = project / "videos"
        videos.mkdir(parents=True)
        one, two = videos / "one.mp4", videos / "two.mp4"
        make_clip(one, "red")
        make_clip(two, "blue")
        state = {
            "segments": {"S01": {"current_video_id": "V1"}, "S02": {"current_video_id": "V2"}},
            "videos": {
                "V1": {"segment_id": "S01", "status": "accepted", "output": {"path": "videos/one.mp4", "sha256": sha256(one)}},
                "V2": {"segment_id": "S02", "status": "accepted", "output": {"path": "videos/two.mp4", "sha256": sha256(two)}},
            },
        }
        (project / "video-project.json").write_text(json.dumps(state), encoding="utf-8")
        plan = project / "delivery" / "plan.json"
        self.assertEqual(main(["plan", "--project-dir", str(project), "--output-plan", str(plan)]), 0)
        data = json.loads(plan.read_text())
        data["clips"][1]["in_frame"] = 12
        plan.write_text(json.dumps(data), encoding="utf-8")
        output, manifest, qa = project / "delivery" / "film.mp4", project / "delivery" / "manifest.json", project / "delivery" / "qa"
        self.assertEqual(main(["build", "--project-dir", str(project), "--plan", str(plan), "--output", str(output), "--manifest", str(manifest), "--qa-dir", str(qa)]), 0)
        result = json.loads(manifest.read_text())
        self.assertEqual(result["clips"][1]["source_window_frames"], [12, 24])
        self.assertEqual(result["join_frames"], [24])
        self.assertEqual(probe(output)["frames"], 36)
        self.assertEqual(len(list(qa.glob("join-*.jpg"))), 1)

    def test_plan_rejects_nonaccepted_current_video(self) -> None:
        project = self.root / "project"
        project.mkdir()
        (project / "video-project.json").write_text(json.dumps({"segments": {"S01": {"current_video_id": "V1"}}, "videos": {"V1": {"segment_id": "S01", "status": "generated"}}}), encoding="utf-8")
        self.assertEqual(main(["plan", "--project-dir", str(project), "--output-plan", str(project / "plan.json")]), 2)


if __name__ == "__main__":
    unittest.main()
