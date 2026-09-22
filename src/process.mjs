import { spawn } from "node:child_process";
import { resolveExecutable, runtimeEnvironment } from "./runtime.mjs";

export function run(command, args = [], options = {}) {
  const resolved = resolveExecutable(command, options);
  return new Promise((resolve) => {
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const child = spawn(resolved.command, [...resolved.argsPrefix, ...args], {
      cwd: options.cwd,
      env: { ...process.env, ...(options.env || {}), ...runtimeEnvironment(options), ...resolved.envPatch },
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true
    });
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (error) => resolve({ code: 127, stdout, stderr: `${stderr}${error.message}`, timedOut, resolvedCommand: resolved.command, resolution: resolved.resolution }));
    let timer = null;
    if (options.timeoutMs) {
      timer = setTimeout(() => {
        timedOut = true;
        child.kill("SIGTERM");
      }, options.timeoutMs);
    }
    child.on("close", (code) => {
      if (timer) clearTimeout(timer);
      resolve({ code: code ?? 1, stdout, stderr, timedOut, resolvedCommand: resolved.command, resolution: resolved.resolution });
    });
  });
}

export function runInherited(command, args = [], options = {}) {
  const resolved = resolveExecutable(command, options);
  return new Promise((resolve, reject) => {
    const child = spawn(resolved.command, [...resolved.argsPrefix, ...args], {
      cwd: options.cwd,
      env: { ...process.env, ...(options.env || {}), ...runtimeEnvironment(options), ...resolved.envPatch },
      stdio: "inherit",
      windowsHide: true
    });
    child.on("error", reject);
    child.on("close", (code) => resolve({ code: code ?? 1 }));
  });
}
