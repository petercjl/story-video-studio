import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "dependencies.json"), "utf8"));
const suite = JSON.parse(fs.readFileSync(path.join(root, "suite.json"), "utf8"));
const errors = [];
const declared = new Set(manifest.bundled_skills);
const actual = new Set(suite.bundled_skills.map((item) => item.name));
for (const name of declared) if (!actual.has(name)) errors.push(`bundled dependency missing from suite: ${name}`);
for (const name of actual) if (!declared.has(name)) errors.push(`suite Skill missing from dependencies.json: ${name}`);
for (const item of suite.bundled_skills) {
  const skillRoot = path.join(root, "skills", item.name);
  const skill = path.join(skillRoot, "SKILL.md");
  if (!fs.existsSync(skill)) errors.push(`missing SKILL.md: ${item.name}`);
  const content = fs.readFileSync(skill, "utf8");
  for (const match of content.matchAll(/\]\(([^)#]+)(?:#[^)]+)?\)/g)) {
    const target = match[1];
    if (/^[a-z]+:/i.test(target)) continue;
    if (!fs.existsSync(path.resolve(skillRoot, target))) errors.push(`${item.name}: broken relative link ${target}`);
  }
}
for (const file of ["capabilities.json", "adapters/codex.json", "adapters/sealseek-openclaw.json"]) {
  for (const item of suite.bundled_skills) {
    const candidate = path.join(root, "skills", item.name, file);
    if (fs.existsSync(candidate)) {
      try { JSON.parse(fs.readFileSync(candidate, "utf8")); }
      catch (error) { errors.push(`${path.relative(root, candidate)}: invalid JSON (${error.message})`); }
    }
  }
}
if (errors.length) {
  process.stderr.write(`${errors.join("\n")}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(`Dependency contract valid: ${actual.size} bundled Skills, ${manifest.runtime_skills.length} Agent Skills, ${manifest.host_capabilities.length} host capabilities.\n`);
}

