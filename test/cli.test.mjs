import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const root = path.resolve(import.meta.dirname, "..");
const bin = path.join(root, "bin", "story-video-studio.mjs");

function cli(args, env = {}) {
  return spawnSync(process.execPath, [bin, ...args], { encoding: "utf8", env: { ...process.env, STORY_VIDEO_STUDIO_AUTO_UPDATE: "off", ...env } });
}

test("capabilities and errors use structured JSON", () => {
  const capabilities = cli(["capabilities", "--json"]);
  assert.equal(capabilities.status, 0, capabilities.stderr);
  assert.equal(JSON.parse(capabilities.stdout).data.automatic_updates.registry_check_hours, 6);
  const invalid = cli(["unknown", "--json"]);
  assert.equal(invalid.status, 1);
  assert.equal(JSON.parse(invalid.stdout).error.code, "COMMAND_UNKNOWN");
});

test("preflight returns canonical paths after a managed installation", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-cli-"));
  const env = { CODEX_HOME: path.join(temporary, "codex") };
  const installed = cli(["skill", "install", "--agent", "codex", "--copy", "--json"], env);
  assert.equal(installed.status, 0, installed.stdout + installed.stderr);
  const preflight = cli(["preflight", "--agent", "codex", "--json"], env);
  assert.equal(preflight.status, 0, preflight.stdout + preflight.stderr);
  const data = JSON.parse(preflight.stdout).data;
  assert.equal(data.ready, true);
  assert.equal(data.canonical_skills.length, 6);
  fs.rmSync(temporary, { recursive: true, force: true });
});

test("automatic update settings persist outside the package", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-config-"));
  const config = path.join(temporary, "config.json");
  const env = { STORY_VIDEO_STUDIO_CONFIG: config };
  const changed = cli(["settings", "set", "update-check-hours", "6", "--json"], env);
  assert.equal(changed.status, 0, changed.stderr);
  assert.equal(JSON.parse(fs.readFileSync(config, "utf8")).settings.update_check_hours, 6);
  fs.rmSync(temporary, { recursive: true, force: true });
});

