from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from bind_references import asset_record, main as bind_references
from reference_request import load, sha, split_draft_prompt


class ProjectHandoffTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.story = self.root / "story.txt"
        self.story.write_text("A complete story beat", encoding="utf-8")
        self.draft = self.root / "draft.txt"
        self.draft.write_text(
            "SCENE CONTEXT\nA person opens the door.\nLOCATION MAP\nThe door is behind them.\nACTION\nThey enter.\n",
            encoding="utf-8",
        )
        self.request = self.root / "request.json"
        self.write_request()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_request(self) -> None:
        self.request.write_text(json.dumps({
            "schema": "ai-video-reference-asset-request", "schema_version": "1.0.0",
            "source": {
                "segment_id": "S01", "story_path": "story.txt", "story_sha256": sha(self.story),
                "prompt_path": "draft.txt", "prompt_sha256": sha(self.draft),
            },
            "shots": [{"id": "SH01", "start_seconds": 0, "end_seconds": 12, "visible_task": "Enter"}],
            "assets": [{
                "asset_id": "C01", "name": "Person", "kind": "character", "asset_form": "single-image",
                "brief": "Person identity", "consumer_shots": ["SH01"], "dependencies": [],
            }],
        }), encoding="utf-8")

    def test_request_checks_draft_without_blank_separator(self) -> None:
        self.assertEqual(load(self.request)["source"]["segment_id"], "S01")
        context, rest = split_draft_prompt(self.draft)
        self.assertEqual(context, "SCENE CONTEXT\nA person opens the door.")
        self.assertTrue(rest.startswith("LOCATION MAP\n"))

    def test_request_rejects_prebound_references(self) -> None:
        self.draft.write_text("SCENE CONTEXT\nA person enters.\nACTIVE REFERENCES\n@image1\nACTION\nEnter.\n", encoding="utf-8")
        self.write_request()
        with self.assertRaisesRegex(ValueError, "binding pass"):
            load(self.request)

    def test_asset_package_requires_string_output(self) -> None:
        image = self.root / "person.png"
        image.write_bytes(b"candidate image")
        package = self.root / "package.json"
        package.write_text(json.dumps({
            "schema": "ai-video-reference-asset-package",
            "assets": [{"asset_id": "C01", "status": "approved", "approval": {"status": "approved"},
                        "output": {"path": "person.png"}}],
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "relative image path string"):
            asset_record(package, "C01", image)

    def bind(self, output_name: str, *extra: str) -> dict:
        image = self.root / "person.png"
        image.write_bytes(b"candidate image")
        package = self.root / "package.json"
        package.write_text(json.dumps({
            "schema": "ai-video-reference-asset-package",
            "assets": [{"asset_id": "C01", "status": "approved", "approval": {"status": "approved"},
                        "output": "person.png"}],
        }), encoding="utf-8")
        bindings = self.root / "bindings.json"
        bindings.write_text(json.dumps({"images": [{
            "asset_id": "C01", "package": "package.json", "path": "person.png",
            "classification": "normal", "description": "Person",
        }]}), encoding="utf-8")
        output = self.root / output_name
        argv = [
            "--request", str(self.request), "--draft", str(self.draft),
            "--bindings", str(bindings), "--output-dir", str(output),
            "--duration", "12", *extra,
        ]
        self.assertEqual(bind_references(argv), 0)
        return json.loads((output / "input-map.json").read_text(encoding="utf-8"))

    def test_input_map_uses_automatic_model_routing_by_default(self) -> None:
        self.assertNotIn("model", self.bind("auto-output"))

    def test_input_map_preserves_explicit_model_override(self) -> None:
        data = self.bind("override-output", "--model", "provider-model-id")
        self.assertEqual(data["model"], "provider-model-id")


if __name__ == "__main__":
    unittest.main()
