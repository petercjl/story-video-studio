import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

function packageBinary(packageName, exists) {
  try {
    const candidate = require(packageName).path;
    return candidate && exists(candidate) ? candidate : null;
  } catch {
    return null;
  }
}

function managedPython(execPath, platform, exists) {
  if (platform !== "win32") return null;
  const api = path.win32;
  const nodeVersionDir = api.dirname(execPath);
  const binariesRoot = api.resolve(nodeVersionDir, "..", "..", "..");
  const candidates = [
    api.join(binariesRoot, "python", "envs", "default", "Scripts", "python.exe"),
    api.join(binariesRoot, "python", "python.exe")
  ];
  return candidates.find((candidate) => exists(candidate)) || null;
}

export function resolveExecutable(command, options = {}) {
  const platform = options.platform || process.platform;
  const execPath = options.execPath || process.execPath;
  const env = { ...process.env, ...(options.env || {}) };
  const exists = options.exists || fs.existsSync;
  if (command === "node") {
    return { command: execPath, argsPrefix: [], resolution: "active-node", envPatch: {} };
  }
  if (command === "npm" && platform === "win32") {
    const nodeDir = path.win32.dirname(execPath);
    const npmCli = path.win32.join(nodeDir, "node_modules", "npm", "bin", "npm-cli.js");
    if (exists(npmCli)) {
      const managedRoot = path.win32.dirname(nodeDir);
      return {
        command: execPath,
        argsPrefix: [npmCli],
        resolution: "managed-node-npm-cli",
        envPatch: {
          npm_config_prefix: env.npm_config_prefix || path.win32.join(managedRoot, "global"),
          npm_config_cache: env.npm_config_cache || path.win32.join(managedRoot, "cache")
        }
      };
    }
  }
  if (["python", "python3"].includes(command)) {
    const configured = env.STORY_VIDEO_PYTHON || env.SEALSEEK_PYTHON;
    if (configured && exists(configured)) return { command: configured, argsPrefix: [], resolution: "configured-python", envPatch: {} };
    const managed = managedPython(execPath, platform, exists);
    if (managed) return { command: managed, argsPrefix: [], resolution: "managed-sealseek-python", envPatch: {} };
    return { command: platform === "win32" ? "python.exe" : "python3", argsPrefix: [], resolution: "path", envPatch: {} };
  }
  if (command === "ffmpeg" || command === "ffprobe") {
    const configured = command === "ffmpeg" ? env.STORY_VIDEO_FFMPEG : env.STORY_VIDEO_FFPROBE;
    if (configured && exists(configured)) return { command: configured, argsPrefix: [], resolution: "configured-media-tool", envPatch: {} };
    const packaged = packageBinary(command === "ffmpeg" ? "@ffmpeg-installer/ffmpeg" : "@ffprobe-installer/ffprobe", exists);
    if (packaged) return { command: packaged, argsPrefix: [], resolution: "bundled-media-tool", envPatch: {} };
  }
  return { command, argsPrefix: [], resolution: "path", envPatch: {} };
}

export function runtimeEnvironment(options = {}) {
  const platform = options.platform || process.platform;
  const env = { ...process.env, ...(options.env || {}) };
  const delimiter = platform === "win32" ? ";" : ":";
  const api = platform === "win32" ? path.win32 : path;
  const directories = ["ffmpeg", "ffprobe"]
    .map((name) => resolveExecutable(name, options))
    .filter((entry) => entry.resolution !== "path")
    .map((entry) => api.dirname(entry.command));
  const unique = [...new Set(directories)];
  if (!unique.length) return {};
  return { PATH: [...unique, env.PATH || env.Path || ""].filter(Boolean).join(delimiter) };
}
