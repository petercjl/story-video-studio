import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const packageRoot = path.resolve(here, "..");
export const binScript = path.join(packageRoot, "bin", "story-video-studio.mjs");
export const bundledSkillsRoot = path.join(packageRoot, "skills");
export const suiteManifestPath = path.join(packageRoot, "suite.json");

export function configPath(env = process.env, platform = process.platform, home = os.homedir()) {
  if (env.STORY_VIDEO_STUDIO_CONFIG) return path.resolve(env.STORY_VIDEO_STUDIO_CONFIG);
  const api = platform === "win32" ? path.win32 : path;
  const base = platform === "win32"
    ? (env.APPDATA || api.join(home, "AppData", "Roaming"))
    : (env.XDG_CONFIG_HOME || api.join(home, ".config"));
  return api.join(base, "story-video-studio", "config.json");
}

export function updateStatePath() {
  if (process.env.STORY_VIDEO_STUDIO_UPDATE_STATE) return path.resolve(process.env.STORY_VIDEO_STUDIO_UPDATE_STATE);
  return path.join(path.dirname(configPath()), "update-state.json");
}

export function updateLockPath() {
  return path.join(path.dirname(updateStatePath()), "update.lock");
}

export function skillRoot(agent, options = {}) {
  const home = options.home || os.homedir();
  const env = options.env || process.env;
  const platform = options.platform || process.platform;
  const exists = options.exists || fs.existsSync;
  const api = platform === "win32" ? path.win32 : path;
  if (agent === "codex") return api.join(env.CODEX_HOME || api.join(home, ".codex"), "skills");
  if (agent === "sealseek") {
    if (env.SEALSEEK_SKILLS_HOME) return path.resolve(env.SEALSEEK_SKILLS_HOME);
    const workspace = api.join(home, ".sealseek", "workspace");
    if (platform === "win32" && (exists(workspace) || exists(api.dirname(workspace)))) return api.join(workspace, "skills");
    return api.join(home, ".agents", "skills");
  }
  throw new Error(`Unknown Agent: ${agent}`);
}

export function skillTarget(agent, skillName, options = {}) {
  const platform = options.platform || process.platform;
  const api = platform === "win32" ? path.win32 : path;
  return api.join(skillRoot(agent, options), skillName);
}

