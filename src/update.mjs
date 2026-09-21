import fs from "node:fs";
import path from "node:path";
import { loadConfig } from "./config.mjs";
import { binScript, packageRoot, updateLockPath, updateStatePath } from "./paths.mjs";
import { run, runInherited } from "./process.mjs";
import { skillStatus } from "./skill.mjs";
import { CliError } from "./errors.mjs";

const DEFAULT_INTERVAL_HOURS = 6;
const DEFAULT_MIRROR_REGISTRY = "https://registry.npmmirror.com/";
const UPDATE_TIMEOUT_MS = 8000;
const UPDATE_GUARD = "STORY_VIDEO_STUDIO_AUTO_UPDATE_GUARD";
const REFRESH_AGENTS = "STORY_VIDEO_STUDIO_REFRESH_AGENTS";
const LOCK_STALE_MS = 15 * 60 * 1000;

function numericParts(version) {
  return String(version).replace(/^v/, "").split(/[.+-]/).slice(0, 3).map((part) => Number(part) || 0);
}

export function isNewerVersion(candidate, current) {
  const left = numericParts(candidate);
  const right = numericParts(current);
  for (let index = 0; index < 3; index += 1) {
    if (left[index] !== right[index]) return left[index] > right[index];
  }
  return false;
}

function readJson(filename) {
  try { return JSON.parse(fs.readFileSync(filename, "utf8")); }
  catch { return {}; }
}

function writeJson(filename, value) {
  fs.mkdirSync(path.dirname(filename), { recursive: true, mode: 0o700 });
  const temporary = `${filename}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, filename);
  try { fs.chmodSync(filename, 0o600); } catch {}
}

function automaticUpdateEnabled(config, env) {
  const override = env.STORY_VIDEO_STUDIO_AUTO_UPDATE?.toLowerCase();
  if (["0", "false", "off", "no"].includes(override)) return false;
  if (["1", "true", "on", "yes"].includes(override)) return true;
  return config.settings?.auto_update !== false;
}

function normalizeRegistry(value) {
  const text = String(value || "").trim();
  if (!/^https?:\/\//i.test(text)) return null;
  return text.endsWith("/") ? text : `${text}/`;
}

function uniqueRegistries(values) {
  return [...new Set(values.map(normalizeRegistry).filter(Boolean))];
}

export async function resolveUpdateRegistries(config, dependencies = {}) {
  const env = dependencies.env || process.env;
  const execute = dependencies.run || run;
  const configured = config.settings?.update_registry;
  const overrides = String(env.STORY_VIDEO_STUDIO_UPDATE_REGISTRY || "").split(",").map((item) => item.trim()).filter(Boolean);
  const preferred = configured && configured !== "auto" ? [configured] : [];
  let npmRegistry = null;
  try {
    const result = await execute("npm", ["config", "get", "registry"], { env, timeoutMs: dependencies.timeoutMs || UPDATE_TIMEOUT_MS });
    if (result.code === 0) npmRegistry = result.stdout.trim();
  } catch {}
  return uniqueRegistries([...overrides, ...preferred, npmRegistry, DEFAULT_MIRROR_REGISTRY]);
}

export async function queryLatestVersion(pkg, config, dependencies = {}) {
  const env = dependencies.env || process.env;
  const execute = dependencies.run || run;
  const registries = dependencies.registries || await resolveUpdateRegistries(config, dependencies);
  const attempts = [];
  for (const registry of registries) {
    let result;
    try {
      result = await execute("npm", ["view", pkg.name, "version", "--json", "--registry", registry], {
        env: { ...env, npm_config_fetch_timeout: env.npm_config_fetch_timeout || "5000", npm_config_fetch_retries: "0" },
        timeoutMs: dependencies.timeoutMs || UPDATE_TIMEOUT_MS
      });
    } catch (error) {
      attempts.push({ registry, ok: false, detail: error.message });
      continue;
    }
    if (result.code !== 0) {
      attempts.push({ registry, ok: false, detail: result.timedOut ? "timed out" : (result.stderr.trim() || "registry query failed") });
      continue;
    }
    let latest;
    try { latest = JSON.parse(result.stdout.trim()); }
    catch { latest = result.stdout.trim().replace(/^"|"$/g, ""); }
    attempts.push({ registry, ok: true, latest });
    return { ok: true, latest, registry, attempts };
  }
  return { ok: false, attempts };
}

function registryFailureMessage(attempts) {
  if (!attempts.length) return "No valid npm update registry is configured.";
  return `Unable to check npm for updates: ${attempts.map((item) => `${item.registry} (${item.detail})`).join("; ")}`;
}

function acquireLock(filename) {
  fs.mkdirSync(path.dirname(filename), { recursive: true, mode: 0o700 });
  try {
    const fd = fs.openSync(filename, "wx", 0o600);
    fs.writeFileSync(fd, `${JSON.stringify({ pid: process.pid, created_at: new Date().toISOString() })}\n`);
    return () => { try { fs.closeSync(fd); } catch {} try { fs.unlinkSync(filename); } catch {} };
  } catch (error) {
    if (error.code !== "EEXIST") throw error;
    const stat = fs.statSync(filename);
    if (Date.now() - stat.mtimeMs > LOCK_STALE_MS) {
      fs.unlinkSync(filename);
      return acquireLock(filename);
    }
    throw new CliError("UPDATE_IN_PROGRESS", "Another story-video-studio update is already in progress.", readJson(filename));
  }
}

async function installPackage(pkg, version, registry, dependencies = {}) {
  const execute = dependencies.run || run;
  return execute("npm", ["install", "--global", `${pkg.name}@${version}`, "--registry", registry], {
    env: dependencies.env || process.env,
    timeoutMs: dependencies.installTimeoutMs || 180000
  });
}

function managedAgents() {
  return skillStatus("all").filter((entry) => entry.installed).map((entry) => entry.agent);
}

export async function maybeAutoUpdate(rawArgs, pkg, dependencies = {}, options = {}) {
  const env = dependencies.env || process.env;
  if (env[UPDATE_GUARD] === "1") return { checked: false, reason: "guard" };
  const sourceCheckout = dependencies.sourceCheckout ?? fs.existsSync(path.join(packageRoot, ".git"));
  if (!options.force && sourceCheckout) return { checked: false, reason: "source-checkout" };
  const config = (dependencies.loadConfig || loadConfig)();
  if (!options.force && !automaticUpdateEnabled(config, env)) return { checked: false, reason: "disabled" };

  const stateFile = dependencies.stateFile || updateStatePath();
  const now = dependencies.now?.() || Date.now();
  const intervalHours = Number(config.settings?.update_check_hours ?? DEFAULT_INTERVAL_HOURS);
  const intervalMs = Math.max(0, intervalHours) * 60 * 60 * 1000;
  const state = readJson(stateFile);
  if (!options.force && intervalMs > 0 && Number.isFinite(state.last_checked_at) && now - state.last_checked_at < intervalMs) {
    return { checked: false, reason: "fresh", latest: state.latest || null, registry: state.registry || null };
  }

  const query = await queryLatestVersion(pkg, config, dependencies);
  if (!query.ok) return { checked: true, warning: registryFailureMessage(query.attempts), attempts: query.attempts };
  const { latest, registry } = query;
  writeJson(stateFile, { last_checked_at: now, latest, current: pkg.version, registry });
  if (!isNewerVersion(latest, pkg.version)) return { checked: true, updated: false, latest, registry, attempts: query.attempts };

  const release = acquireLock(dependencies.lockFile || updateLockPath());
  const agentsToRefresh = dependencies.managedAgents ? dependencies.managedAgents() : managedAgents();
  try {
    const install = await installPackage(pkg, "latest", registry, dependencies);
    if (install.code !== 0) throw new CliError("UPDATE_INSTALL_FAILED", install.stderr.trim() || "Automatic npm update failed.", { latest, registry });
    const reexecute = dependencies.runInherited || runInherited;
    const child = await reexecute(process.execPath, [binScript, ...rawArgs], {
      env: { ...env, [UPDATE_GUARD]: "1", [REFRESH_AGENTS]: agentsToRefresh.join(",") }
    });
    if ((child.code ?? 1) !== 0) {
      const rollback = await installPackage(pkg, pkg.version, registry, dependencies);
      throw new CliError("UPDATE_REFRESH_FAILED", "The new package installed but Skill refresh or command restart failed. The previous npm version was restored.", { latest, registry, rollback_ok: rollback.code === 0 });
    }
    return { checked: true, updated: true, latest, registry, reexecuted: true, exitCode: child.code ?? 0 };
  } finally {
    release();
  }
}

export function refreshAgentsFromEnvironment(env = process.env) {
  return String(env[REFRESH_AGENTS] || "").split(",").map((item) => item.trim()).filter(Boolean);
}
