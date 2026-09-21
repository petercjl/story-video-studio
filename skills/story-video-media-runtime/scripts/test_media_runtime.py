#!/usr/bin/env python3

import functools
import hashlib
import http.server
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


router = load("select_video_model")
materializer = load("materialize_artifact")


class RouteTests(unittest.TestCase):
    def test_spoken_performance_uses_25_on_sealseek(self):
        result = router.select("sealseek-openclaw", {"duration_seconds": 10, "resolution": "720p", "spoken_performance": True})
        self.assertEqual(result["selected_model"], "doubao-seedance-2-5")

    def test_multishot_uses_20(self):
        result = router.select("sealseek-openclaw", {"duration_seconds": 10, "resolution": "720p", "multi_shot_continuity": True})
        self.assertEqual(result["selected_model"], "doubao-seedance-2-0-fast")

    def test_codex_defers_effective_model(self):
        result = router.select("codex", {"duration_seconds": 10, "spoken_performance": True})
        self.assertEqual(result["selected_model"], "auto")

    def test_impossible_duration_resolution_combination(self):
        result = router.select("sealseek-openclaw", {"duration_seconds": 20, "resolution": "1080p"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "FEATURE_UNSUPPORTED")

    def test_explicit_override(self):
        result = router.select("sealseek-openclaw", {"explicit_model": "chosen-model"})
        self.assertEqual(result["selected_model"], "chosen-model")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class MaterializeTests(unittest.TestCase):
    def serve(self, directory: Path):
        handler = functools.partial(QuietHandler, directory=str(directory))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server

    def test_download_hash_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as output_dir:
            payload = b"\x89PNG\r\n\x1a\n" + b"story-video-test"
            (Path(source_dir) / "sample.png").write_bytes(payload)
            server = self.serve(Path(source_dir))
            try:
                output = Path(output_dir) / "saved.png"
                url = f"http://127.0.0.1:{server.server_port}/sample.png"
                result = materializer.materialize(url, output, "image")
                self.assertTrue(result["ok"])
                self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
                self.assertEqual(materializer.materialize(url, output, "image")["error"]["code"], "TARGET_EXISTS")
            finally:
                server.shutdown()
                server.server_close()

    def test_reject_html_body(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as output_dir:
            (Path(source_dir) / "error.html").write_text("<html>provider error</html>", encoding="utf-8")
            server = self.serve(Path(source_dir))
            try:
                url = f"http://127.0.0.1:{server.server_port}/error.html"
                self.assertFalse(materializer.materialize(url, Path(output_dir) / "bad.mp4", "video")["ok"])
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
