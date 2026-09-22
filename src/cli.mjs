import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { loadConfig, saveConfig } from "./config.mjs";
import { CliError, requireValue } from "./errors.mjs";
import { run, runInherited } from "./process.mjs";
import { skillInstall, skillSource, skillStatus } from "./skill.mjs";
import { validateBundledSuite } from "./suite.mjs";
import { maybeAutoUpdate, refreshAgentsFromEnvironment } from "./update.mjs";
import { bundledSkillsRoot } from "./paths.mjs";

const require = createRequire(import.meta.url);
const pkg = require("../package.json");

const CAPABILITIES = {
  schema: "story-video-studio-capabilities",
  schema_version: 1,
  package: pkg.name,
  version: pkg.version,
  commands: ["version", "capabilities", "doctor", "setup", "preflight", "run-script", "settings", "skill", "update"],
  automatic_updates: { enabled_by_default: true, registry_check_hours: 6, refreshes_installed_suite: true, reexecutes_command: true },
  agents: { codex_macos: "tested", sealseek_windows: "implemented", sealseek_macos: "spec-compatible" },
  credentials: "host-managed",
  media_execution: "platform-adapter"
};

function option(args, name) {
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] === name) {
      if (index + 1 >= args.length) throw new CliError("ARGUMENT_REQUIRED", `${name} requires a value.`);
      return args.splice(index, 2)[1];
    }
    if (args[index].startsWith(`${name}=`)) return args.splice(index, 1)[0].slice(name.length + 1);
  }
  return undefined;
}

function flag(args, name) {
  const index = args.indexOf(name);
  if (index < 0) return false;
  args.splice(index, 1);
  return true;
}

function output(value, json) {
  if (json) process.stdout.write(`${JSON.stringify({ ok: true, data: value }, null, 2)}\n`);
  else if (typeof value === "string") process.stdout.write(`${value}\n`);
  else process.stdout.write(`${JSON.stringify(value, null, 2)}\n`);
}

function help() {
  return `story-video-studio ${pkg.version}\n\n` +
    `Commands:\n` +
    `  version | capabilities\n` +
    `  doctor --agent <codex|sealseek|all>\n` +
    `  setup --agent <codex|sealseek>\n` +
    `  preflight --agent <codex|sealseek> [--node <project|story|segments|prompt-pass-1|assets|prompt-pass-2|video-generation|video-qa|delivery>]\n` +
    `  run-script <skill-name> <script.py> [arguments...]\n` +
    `  settings show | set auto-update <on|off> | set update-check-hours <hours> | set update-registry <auto|url>\n` +
    `  skill source\n` +
    `  skill status|install|update --agent <codex|sealseek|all> [--copy] [--adopt]\n` +
    `  update --agent <codex|sealseek|all>\n\n` +
    `Use --json for machine-readable output.`;
}

async function commandCheck(command, args = ["--version"], requiredFor = []) {
  const result = await run(command, args, { timeoutMs: 10000 });
  return {
    id: `runtime.${command === "python3" ? "python" : command}`,
    ok: result.code === 0,
    required_for: requiredFor,
    detail: (result.stdout || result.stderr).trim().split("\n")[0] || `exit ${result.code}`,
    resolved_command: result.resolvedCommand,
    resolution: result.resolution
  };
}

const NODE_REQUIREMENTS = {
  project: [],
  story: ["python"],
  segments: ["python"],
  "prompt-pass-1": ["python"],
  assets: ["python"],
  "prompt-pass-2": ["python"],
  "video-generation": ["python"],
  "video-qa": ["python", "ffmpeg", "ffprobe"],
  delivery: ["python", "ffmpeg", "ffprobe"]
};

function readinessState(name, checks, requiredIds, detail = null) {
  const relevant = checks.filter((item) => requiredIds.includes(item.id));
  return { name, ready: relevant.every((item) => item.ok), checks: relevant.map((item) => item.id), detail };
}

async function doctor(agent) {
  const checks = [];
  checks.push(await commandCheck("node", ["--version"], ["suite"]));
  checks.push(await commandCheck("npm", ["--version"], ["suite", "updates"]));
  checks.push(await commandCheck("python3", ["--version"], ["story", "segments", "prompts", "assets", "video-generation", "video-qa", "delivery"]));
  checks.push(await commandCheck("ffmpeg", ["-version"], ["video-qa", "assembly", "delivery"]));
  checks.push(await commandCheck("ffprobe", ["-version"], ["video-qa", "assembly", "delivery"]));
  const suite = validateBundledSuite();
  checks.push({ id: "suite.integrity", ok: suite.ok, required_for: ["suite"], detail: suite.checks });
  for (const status of skillStatus(agent)) {
    checks.push({ id: `skills.${status.agent}.managed`, ok: status.skills.every((item) => item.managed && item.current), required_for: ["suite"], detail: status });
    for (const external of status.external) checks.push({ id: `dependency.${status.agent}.${external.name}`, ok: external.installed || !external.required, required_for: external.required ? ["suite"] : [], detail: external });
  }
  const suiteIds = ["runtime.node", "runtime.npm", "suite.integrity", ...checks.filter((item) => item.id.startsWith("skills.") || item.id.startsWith("dependency.")).map((item) => item.id)];
  const pythonIds = ["runtime.python"];
  const mediaIds = ["runtime.ffmpeg", "runtime.ffprobe"];
  const readiness = {
    suite_ready: readinessState("suite", checks, suiteIds),
    story_ready: readinessState("story", checks, [...suiteIds, ...pythonIds]),
    generation_ready: { name: "generation", ready: readinessState("generation", checks, [...suiteIds, ...pythonIds]).ready, checks: [...suiteIds, ...pythonIds], detail: "Provider capability and credentials are validated by the active Agent adapter at submission time." },
    media_ready: readinessState("media", checks, mediaIds),
    assembly_ready: readinessState("assembly", checks, [...pythonIds, ...mediaIds]),
    delivery_ready: { ...readinessState("delivery", checks, [...pythonIds, ...mediaIds]), detail: "BGM generation remains provider-dependent and is checked when requested." }
  };
  return { ok: readiness.suite_ready.ready, package: pkg.name, version: pkg.version, readiness, checks };
}

async function preflight(agent, node = "project") {
  if (!agent || agent === "all") throw new CliError("AGENT_REQUIRED", "preflight requires exactly one --agent codex or sealseek.");
  if (!Object.hasOwn(NODE_REQUIREMENTS, node)) throw new CliError("NODE_UNKNOWN", `Unsupported workflow node: ${node}`, { allowed: Object.keys(NODE_REQUIREMENTS) });
  const validation = validateBundledSuite();
  if (!validation.ok) throw new CliError("SUITE_VALIDATION_FAILED", "Bundled Skill suite failed integrity validation.", validation.checks);
  const status = skillStatus(agent)[0];
  if (!status.skills.every((item) => item.managed && item.current)) {
    throw new CliError("SKILL_SUITE_NOT_CURRENT", `The managed Skill suite is missing or stale for ${agent}.`, { status, repair: `story-video-studio skill install --agent ${agent}` });
  }
  const missing = status.external.filter((item) => item.required && !item.installed);
  if (missing.length) throw new CliError("CAPABILITY_UNAVAILABLE", "Required external Skills are missing.", missing);
  const runtimeChecks = [];
  for (const requirement of NODE_REQUIREMENTS[node]) {
    const command = requirement === "python" ? "python3" : requirement;
    const args = requirement.startsWith("ff") ? ["-version"] : ["--version"];
    runtimeChecks.push(await commandCheck(command, args, [node]));
  }
  const unavailable = runtimeChecks.filter((item) => !item.ok);
  if (unavailable.length) throw new CliError("RUNTIME_UNAVAILABLE", `Workflow node ${node} is not ready.`, { node, checks: unavailable, repair: `story-video-studio setup --agent ${agent} --json` });
  const source = skillSource();
  return {
    ready: true,
    agent,
    node,
    package: pkg.name,
    package_version: pkg.version,
    suite_version: source.suite_version,
    entry_skill: source.entry_skill,
    canonical_skills: source.skills,
    runtime_checks: runtimeChecks,
    instruction: "Use the canonical Skill path returned for the current node. If this preflight followed an update, reload that SKILL.md before continuing."
  };
}

async function setup(agent) {
  if (!agent || agent === "all") throw new CliError("AGENT_REQUIRED", "setup requires exactly one --agent codex or sealseek.");
  const prior = skillStatus(agent)[0];
  const mode = prior.installed && prior.skills.some((item) => item.mode === "copy") ? "copy" : "link";
  const installed = skillInstall(agent, mode);
  const diagnosis = await doctor(agent);
  return {
    ready: diagnosis.readiness.suite_ready.ready && diagnosis.readiness.story_ready.ready && diagnosis.readiness.media_ready.ready,
    agent,
    installed,
    managed_media_tools: ["ffmpeg", "ffprobe"],
    diagnosis,
    remediation: diagnosis.readiness.story_ready.ready ? [] : ["Configure STORY_VIDEO_PYTHON with a Python 3 executable, or install Python in the Agent-managed runtime."]
  };
}

async function runScript(args) {
  const skillName = requireValue(args.shift(), "SKILL_REQUIRED", "run-script requires a bundled Skill name.");
  const scriptName = requireValue(args.shift(), "SCRIPT_REQUIRED", "run-script requires a Python script path relative to the Skill scripts directory.");
  const suite = validateBundledSuite();
  if (!suite.ok) throw new CliError("SUITE_VALIDATION_FAILED", "Bundled Skill suite failed integrity validation.", suite.checks);
  if (!suite.suite.bundled_skills.some((item) => item.name === skillName)) throw new CliError("SKILL_UNKNOWN", `Unknown bundled Skill: ${skillName}`);
  const scriptsRoot = path.resolve(bundledSkillsRoot, skillName, "scripts");
  const script = path.resolve(scriptsRoot, scriptName);
  const relative = path.relative(scriptsRoot, script);
  if (!relative || relative.startsWith("..") || path.isAbsolute(relative) || path.extname(script).toLowerCase() !== ".py") throw new CliError("SCRIPT_PATH_INVALID", "Script must be a .py file inside the selected Skill scripts directory.");
  if (!fs.existsSync(script)) throw new CliError("SCRIPT_NOT_FOUND", `Bundled script not found: ${skillName}/scripts/${scriptName}`);
  const result = await runInherited("python3", ["-B", script, ...args], { cwd: process.cwd() });
  if (result.code !== 0) throw new CliError("SCRIPT_FAILED", `Bundled script exited with code ${result.code}.`, { skill: skillName, script: scriptName, exit_code: result.code });
  return result;
}

function refreshManagedAgents() {
  const refreshed = [];
  for (const agent of refreshAgentsFromEnvironment()) {
    const status = skillStatus(agent)[0];
    const mode = status.skills.some((item) => item.mode === "copy") ? "copy" : "link";
    refreshed.push(...skillInstall(agent, mode, { update: true }));
  }
  return refreshed;
}

export async function main(rawArgs) {
  const args = [...rawArgs];
  const json = flag(args, "--json");
  if (args.length === 0 || ["help", "--help", "-h"].includes(args[0])) return output(help(), false);
  const command = args.shift();
  if (command === "version" || command === "--version" || command === "-V") return output(pkg.version, json);

  const refreshed = refreshManagedAgents();
  let updateInfo = null;
  if (!["update", "settings"].includes(command)) {
    updateInfo = await maybeAutoUpdate(rawArgs, pkg);
    if (updateInfo.warning) process.stderr.write(`[AUTO_UPDATE_WARNING] ${updateInfo.warning}\n`);
    if (updateInfo.reexecuted) {
      process.exitCode = updateInfo.exitCode;
      return;
    }
  }

  if (command === "capabilities") return output(CAPABILITIES, json);
  if (command === "settings") {
    const action = args.shift() || "show";
    const config = loadConfig();
    if (action === "show") return output(config.settings, json);
    if (action !== "set") throw new CliError("COMMAND_UNKNOWN", `Unknown settings action: ${action}`);
    const name = requireValue(args.shift(), "SETTING_REQUIRED", "settings set requires a setting name.");
    const value = requireValue(args.shift(), "VALUE_REQUIRED", `settings set ${name} requires a value.`);
    if (name === "auto-update") {
      if (!["on", "off"].includes(value)) throw new CliError("SETTING_INVALID", "auto-update must be on or off.");
      config.settings.auto_update = value === "on";
    } else if (name === "update-check-hours") {
      const hours = Number(value);
      if (!Number.isFinite(hours) || hours < 0) throw new CliError("SETTING_INVALID", "update-check-hours must be zero or a positive number.");
      config.settings.update_check_hours = hours;
    } else if (name === "update-registry") {
      if (value !== "auto" && !/^https?:\/\//i.test(value)) throw new CliError("SETTING_INVALID", "update-registry must be auto or an http(s) URL.");
      config.settings.update_registry = value;
    } else throw new CliError("SETTING_UNKNOWN", `Unknown setting: ${name}`);
    return output({ path: saveConfig(config), settings: config.settings }, json);
  }
  if (command === "doctor") return output(await doctor(option(args, "--agent") || "all"), json);
  if (command === "setup") return output(await setup(option(args, "--agent")), json);
  if (command === "preflight") return output({ ...(await preflight(option(args, "--agent"), option(args, "--node") || "project")), refreshed }, json);
  if (command === "run-script") {
    const result = await runScript(args);
    if (json) return output({ exit_code: result.code }, true);
    return;
  }
  if (command === "skill") {
    const action = args.shift();
    const agent = option(args, "--agent") || "all";
    if (action === "source") return output(skillSource(), json);
    if (action === "status") return output(skillStatus(agent), json);
    if (action === "install") return output(skillInstall(agent, flag(args, "--copy") ? "copy" : "link", { adopt: flag(args, "--adopt") }), json);
    if (action === "update") {
      const requestedMode = flag(args, "--copy") ? "copy" : null;
      const selected = skillStatus(agent).filter((entry) => entry.installed);
      if (!selected.length) throw new CliError("SKILL_NOT_MANAGED", "No managed story-video-studio Skill suite is installed for the selected Agent.");
      const results = selected.flatMap((entry) => {
        const mode = requestedMode || (entry.skills.some((item) => item.mode === "copy") ? "copy" : "link");
        return skillInstall(entry.agent, mode, { update: true });
      });
      return output(results, json);
    }
    throw new CliError("COMMAND_UNKNOWN", `Unknown skill action: ${action || ""}`);
  }
  if (command === "update") {
    const agent = option(args, "--agent") || "all";
    const result = await maybeAutoUpdate(["skill", "update", "--agent", agent, "--json"], pkg, {}, { force: true });
    if (result.warning) throw new CliError("UPDATE_CHECK_FAILED", result.warning, result.attempts);
    if (result.reexecuted) {
      process.exitCode = result.exitCode;
      return;
    }
    const updatedSkills = skillStatus(agent).filter((entry) => entry.installed).flatMap((entry) => {
      const mode = entry.skills.some((item) => item.mode === "copy") ? "copy" : "link";
      return skillInstall(entry.agent, mode, { update: true });
    });
    return output({ ...result, skills: updatedSkills }, json);
  }
  throw new CliError("COMMAND_UNKNOWN", `Unknown command: ${command}`);
}
