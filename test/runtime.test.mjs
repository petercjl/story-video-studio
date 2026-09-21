import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { resolveExecutable } from "../src/runtime.mjs";
import { skillRoot } from "../src/paths.mjs";
import { effectiveSkillMode } from "../src/skill.mjs";

test("Windows SealSeek resolves npm through its managed Node runtime", () => {
  const execPath = "C:\\Users\\employee\\.sealseek\\binaries\\node\\versions\\22.22.2\\node.exe";
  const npmCli = path.win32.join(path.win32.dirname(execPath), "node_modules", "npm", "bin", "npm-cli.js");
  const result = resolveExecutable("npm", { platform: "win32", execPath, env: {}, exists: (candidate) => candidate === npmCli });
  assert.equal(result.command, execPath);
  assert.deepEqual(result.argsPrefix, [npmCli]);
  assert.equal(result.resolution, "managed-node-npm-cli");
});

test("Windows SealSeek uses its active workspace Skill root", () => {
  const home = "C:\\Users\\employee";
  const workspace = path.win32.join(home, ".sealseek", "workspace");
  const result = skillRoot("sealseek", { platform: "win32", home, env: {}, exists: (candidate) => candidate === workspace });
  assert.equal(result, path.win32.join(workspace, "skills"));
});

test("Windows SealSeek receives copies and macOS receives links", () => {
  assert.equal(effectiveSkillMode("sealseek", "link", "win32"), "copy");
  assert.equal(effectiveSkillMode("sealseek", "link", "darwin"), "link");
  assert.equal(effectiveSkillMode("codex", "link", "win32"), "link");
});

