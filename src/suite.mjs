import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { bundledSkillsRoot, suiteManifestPath } from "./paths.mjs";
import { CliError } from "./errors.mjs";

export function loadSuite() {
  const suite = JSON.parse(fs.readFileSync(suiteManifestPath, "utf8"));
  if (suite.schema !== "story-video-skill-suite" || suite.schema_version !== 1) {
    throw new CliError("SUITE_MANIFEST_INVALID", "Unsupported or invalid suite.json.");
  }
  return suite;
}

function filesUnder(root, current = root) {
  const result = [];
  for (const entry of fs.readdirSync(current, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    if ([".DS_Store", ".story-video-studio-runtime.json", "__pycache__", ".pytest_cache"].includes(entry.name) || entry.name.endsWith(".pyc")) continue;
    const absolute = path.join(current, entry.name);
    if (entry.isDirectory()) result.push(...filesUnder(root, absolute));
    else if (entry.isFile()) result.push(path.relative(root, absolute).split(path.sep).join("/"));
  }
  return result;
}

export function directoryDigest(root) {
  const hash = crypto.createHash("sha256");
  let bytes = 0;
  const files = filesUnder(root);
  for (const relative of files) {
    const content = fs.readFileSync(path.join(root, ...relative.split("/")));
    hash.update(relative);
    hash.update("\0");
    hash.update(content);
    hash.update("\0");
    bytes += content.length;
  }
  return { sha256: hash.digest("hex"), files: files.length, bytes };
}

export function validateBundledSuite() {
  const suite = loadSuite();
  const checks = [];
  for (const item of suite.bundled_skills) {
    const root = path.join(bundledSkillsRoot, item.name);
    const exists = fs.existsSync(path.join(root, "SKILL.md"));
    const actual = exists ? directoryDigest(root) : null;
    checks.push({
      name: item.name,
      ok: exists && actual.sha256 === item.sha256 && actual.files === item.files && actual.bytes === item.bytes,
      expected: item,
      actual
    });
  }
  const undeclared = fs.existsSync(bundledSkillsRoot)
    ? fs.readdirSync(bundledSkillsRoot, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => entry.name).filter((name) => !suite.bundled_skills.some((item) => item.name === name))
    : [];
  if (undeclared.length) checks.push({ name: "undeclared", ok: false, actual: undeclared });
  return { ok: checks.every((item) => item.ok), suite, checks };
}
