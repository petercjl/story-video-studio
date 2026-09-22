import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { bundledSkillsRoot, skillRoot, skillTarget } from "./paths.mjs";
import { directoryDigest, loadSuite, validateBundledSuite } from "./suite.mjs";
import { CliError } from "./errors.mjs";

const require = createRequire(import.meta.url);
const pkg = require("../package.json");
export const agents = ["codex", "sealseek"];

function sourceFor(name) {
  return path.join(bundledSkillsRoot, name);
}

function runtimeManifest(target) {
  try { return JSON.parse(fs.readFileSync(path.join(target, ".story-video-studio-runtime.json"), "utf8")); }
  catch { return null; }
}

function targetState(agent, item, options = {}) {
  const target = skillTarget(agent, item.name, options);
  if (!fs.existsSync(target)) return { agent, name: item.name, target, installed: false, managed: false, mode: null, current: false };
  const stat = fs.lstatSync(target);
  if (stat.isSymbolicLink()) {
    let resolved = null;
    try { resolved = fs.realpathSync(target); } catch {}
    const managed = resolved === fs.realpathSync(sourceFor(item.name));
    return { agent, name: item.name, target, installed: true, managed, mode: "link", current: managed, resolved };
  }
  const manifest = runtimeManifest(target);
  const managed = manifest?.package === pkg.name && manifest?.skill === item.name;
  let actual = null;
  if (managed) actual = directoryDigest(target);
  return {
    agent,
    name: item.name,
    target,
    installed: true,
    managed,
    mode: managed ? "copy" : "unmanaged",
    current: Boolean(managed && manifest.suite_version === loadSuite().suite_version && actual?.sha256 === item.sha256),
    installed_version: manifest?.suite_version || null
  };
}

export function skillSource() {
  const suite = loadSuite();
  return {
    package: pkg.name,
    package_version: pkg.version,
    suite_version: suite.suite_version,
    root: bundledSkillsRoot,
    entry_skill: suite.entry_skill,
    skills: suite.bundled_skills.map((item) => ({ name: item.name, path: sourceFor(item.name), sha256: item.sha256 })),
    external_skills: suite.external_skills
  };
}

export function skillStatus(selected = "all", options = {}) {
  const names = selected === "all" ? agents : [selected];
  for (const name of names) if (!agents.includes(name)) throw new CliError("AGENT_UNSUPPORTED", `Unsupported Agent: ${name}`);
  const suite = loadSuite();
  return names.map((agent) => {
    const skills = suite.bundled_skills.map((item) => targetState(agent, item, options));
    const external = suite.external_skills.map((item) => {
      const target = skillTarget(agent, item.name, options);
      return { ...item, target, installed: fs.existsSync(path.join(target, "SKILL.md")) };
    });
    return {
      agent,
      root: skillRoot(agent, options),
      installed: skills.some((item) => item.managed),
      complete: skills.every((item) => item.managed && item.current) && external.filter((item) => item.required).every((item) => item.installed),
      skills,
      external
    };
  });
}

export function effectiveSkillMode(agent, requestedMode, platform = process.platform) {
  if (platform === "win32" && agent === "sealseek" && requestedMode === "link") return "copy";
  return requestedMode;
}

function writeRuntimeManifest(target, item) {
  const manifest = {
    schema: "story-video-studio-skill-runtime",
    schema_version: 1,
    package: pkg.name,
    package_version: pkg.version,
    suite_version: loadSuite().suite_version,
    skill: item.name,
    source_sha256: item.sha256
  };
  fs.writeFileSync(path.join(target, ".story-video-studio-runtime.json"), `${JSON.stringify(manifest, null, 2)}\n`, { mode: 0o600 });
}

function stageOne(agent, item, mode, root) {
  const stage = path.join(root, `.${item.name}.story-video-studio-stage-${process.pid}-${Date.now()}`);
  if (fs.existsSync(stage)) fs.rmSync(stage, { recursive: true, force: true });
  if (mode === "copy") {
    fs.cpSync(sourceFor(item.name), stage, { recursive: true });
    const actual = directoryDigest(stage);
    if (actual.sha256 !== item.sha256) throw new CliError("SKILL_COPY_INVALID", `Staged copy failed validation for ${item.name}.`, { expected: item.sha256, actual: actual.sha256 });
    writeRuntimeManifest(stage, item);
  } else {
    fs.symlinkSync(sourceFor(item.name), stage, process.platform === "win32" ? "junction" : "dir");
  }
  return stage;
}

function clearDirectory(target) {
  for (const entry of fs.readdirSync(target)) fs.rmSync(path.join(target, entry), { recursive: true, force: true });
}

function installCopyInPlace(stage, target) {
  fs.mkdirSync(target, { recursive: true });
  clearDirectory(target);
  for (const entry of fs.readdirSync(stage)) fs.cpSync(path.join(stage, entry), path.join(target, entry), { recursive: true });
}

function restoreCopyInPlace(backup, target) {
  fs.mkdirSync(target, { recursive: true });
  clearDirectory(target);
  for (const entry of fs.readdirSync(backup)) fs.cpSync(path.join(backup, entry), path.join(target, entry), { recursive: true });
}

export function skillInstall(selected = "all", requestedMode = "link", options = {}) {
  const names = selected === "all" ? agents : [selected];
  for (const name of names) if (!agents.includes(name)) throw new CliError("AGENT_UNSUPPORTED", `Unsupported Agent: ${name}`);
  const validation = validateBundledSuite();
  if (!validation.ok) throw new CliError("SUITE_VALIDATION_FAILED", "Bundled Skill suite failed integrity validation.", validation.checks);
  const results = [];
  for (const agent of names) {
    const mode = effectiveSkillMode(agent, requestedMode);
    const root = skillRoot(agent);
    fs.mkdirSync(root, { recursive: true });
    const current = new Map(skillStatus(agent)[0].skills.map((item) => [item.name, item]));
    const conflicts = [...current.values()].filter((item) => item.installed && !item.managed);
    if (conflicts.length && !options.adopt) {
      throw new CliError("SKILL_TARGET_UNMANAGED", "Existing Skill targets are not managed by this package. Re-run with --adopt only after reviewing the listed targets.", conflicts.map((item) => item.target));
    }
    if (options.update && ![...current.values()].some((item) => item.managed)) {
      throw new CliError("SKILL_NOT_MANAGED", `No managed ${pkg.name} Skills are installed for ${agent}. Use skill install first.`);
    }
    const unchanged = [...current.values()].every((item) => item.managed && item.current && item.mode === mode);
    if (unchanged) {
      results.push({ agent, mode, root, unchanged: true, adopted_backups: [], status: skillStatus(agent)[0] });
      continue;
    }
    const staged = [];
    const moved = [];
    try {
      for (const item of validation.suite.bundled_skills) staged.push({ item, stage: stageOne(agent, item, mode, root), target: skillTarget(agent, item.name) });
      for (const entry of staged) {
        let backup = null;
        if (fs.existsSync(entry.target)) {
          const existing = current.get(entry.item.name);
          const keep = existing && !existing.managed;
          backup = path.join(root, `.${entry.item.name}.before-story-video-studio-${new Date().toISOString().replace(/[-:.TZ]/g, "")}`);
          if (mode === "copy" && !fs.lstatSync(entry.target).isSymbolicLink()) {
            fs.cpSync(entry.target, backup, { recursive: true });
            moved.push({ target: entry.target, backup, keep, inPlace: true });
            installCopyInPlace(entry.stage, entry.target);
            fs.rmSync(entry.stage, { recursive: true, force: true });
            continue;
          }
          fs.renameSync(entry.target, backup);
          moved.push({ target: entry.target, backup, keep, inPlace: false });
        }
        fs.renameSync(entry.stage, entry.target);
        moved.push({ target: entry.target, backup: null, installed: true });
      }
      const status = skillStatus(agent)[0];
      if (!status.skills.every((item) => item.managed && item.current)) throw new CliError("SKILL_INSTALL_VALIDATION_FAILED", `Installed Skill suite failed validation for ${agent}.`, status);
      for (const entry of moved.filter((item) => item.backup && !item.keep)) fs.rmSync(entry.backup, { recursive: true, force: true });
      results.push({ agent, mode, root, adopted_backups: moved.filter((item) => item.backup && item.keep).map((item) => item.backup), status });
    } catch (error) {
      for (const entry of staged) if (fs.existsSync(entry.stage)) fs.rmSync(entry.stage, { recursive: true, force: true });
      for (const entry of [...moved].reverse()) {
        if (entry.installed && fs.existsSync(entry.target)) fs.rmSync(entry.target, { recursive: true, force: true });
        if (entry.backup && fs.existsSync(entry.backup)) {
          if (entry.inPlace) restoreCopyInPlace(entry.backup, entry.target);
          else if (!fs.existsSync(entry.target)) fs.renameSync(entry.backup, entry.target);
        }
      }
      throw error;
    }
  }
  return results;
}
