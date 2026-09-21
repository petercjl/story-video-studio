import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { skillInstall, skillStatus } from "../src/skill.mjs";
import { validateBundledSuite } from "../src/suite.mjs";

test("bundled suite matches its release manifest", () => {
  const result = validateBundledSuite();
  assert.equal(result.ok, true, JSON.stringify(result.checks, null, 2));
  assert.equal(result.suite.bundled_skills.length, 6);
  assert.equal(result.suite.external_skills.length, 0);
});

test("copy installation is complete and does not require author paths", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-install-"));
  const prior = process.env.CODEX_HOME;
  process.env.CODEX_HOME = path.join(temporary, "codex");
  try {
    const installed = skillInstall("codex", "copy");
    assert.equal(installed[0].status.skills.length, 6);
    assert.equal(installed[0].status.skills.every((item) => item.managed && item.current), true);
    assert.equal(skillStatus("codex")[0].complete, true);
  } finally {
    if (prior === undefined) delete process.env.CODEX_HOME;
    else process.env.CODEX_HOME = prior;
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("unmanaged targets require explicit adoption and are backed up", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-adopt-"));
  const prior = process.env.CODEX_HOME;
  process.env.CODEX_HOME = path.join(temporary, "codex");
  const target = path.join(process.env.CODEX_HOME, "skills", "story-video-project-studio");
  fs.mkdirSync(target, { recursive: true });
  fs.writeFileSync(path.join(target, "SKILL.md"), "user-owned\n");
  try {
    assert.throws(() => skillInstall("codex", "copy"), (error) => error.code === "SKILL_TARGET_UNMANAGED");
    const installed = skillInstall("codex", "copy", { adopt: true });
    assert.equal(installed[0].adopted_backups.length, 1);
    assert.equal(fs.readFileSync(path.join(installed[0].adopted_backups[0], "SKILL.md"), "utf8"), "user-owned\n");
  } finally {
    if (prior === undefined) delete process.env.CODEX_HOME;
    else process.env.CODEX_HOME = prior;
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

