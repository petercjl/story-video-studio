import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("story_checkpoint.py")


def sample():
    return {
        "schema": "story-development",
        "schema_version": 1,
        "story_id": "sample",
        "title": "Home",
        "premise": "A worker arrives home but keeps answering messages.",
        "story_text": "She answers one last message, hears her cat, and finally says that she is home.",
        "emotional_intent": "Relief after work and the loneliness of an adult homecoming.",
        "opening_question": "Why does she remain at the door?",
        "visible_events": ["She closes the door and replies with both hands on her phone."],
        "continuity_facts": ["She lives alone with an orange cat."],
        "logic_decisions": [{"topic": "sound", "decision": "The cat calls from inside.", "reason": "The sound has a visible source."}],
        "dialogue": [{"speaker": "protagonist", "mode": "spoken", "text": "I am home."}],
        "duration": {"status": "estimated", "requested_seconds": 28, "natural_range_seconds": [35, 50], "approved_seconds": None, "basis": "Four visible actions and one short line."},
        "unresolved": [],
        "review": {"status": "draft", "approved_at": None, "story_sha256": None},
    }


class StoryCheckpointTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_validate_and_approve(self):
        target = self.root / "story-development.json"
        target.write_text(json.dumps(sample()), encoding="utf-8")
        checked = subprocess.run([sys.executable, str(SCRIPT), "validate", str(target)], text=True, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        approved = subprocess.run([sys.executable, str(SCRIPT), "approve", str(target)], text=True, capture_output=True)
        self.assertEqual(approved.returncode, 0, approved.stdout + approved.stderr)
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["review"]["status"], "approved")
        self.assertEqual(len(data["review"]["story_sha256"]), 64)

    def test_rejects_stale_approval_hash(self):
        data = sample()
        data["review"] = {"status": "approved", "approved_at": "2026-01-01T00:00:00Z", "story_sha256": "0" * 64}
        target = self.root / "story-development.json"
        target.write_text(json.dumps(data), encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), "validate", str(target)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not match", result.stdout)


if __name__ == "__main__":
    unittest.main()
