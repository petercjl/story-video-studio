import fs from "node:fs";
import path from "node:path";

export function resolveExecutable(command, options = {}) {
  const platform = options.platform || process.platform;
  const execPath = options.execPath || process.execPath;
  const env = options.env || process.env;
  const exists = options.exists || fs.existsSync;
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
  return { command, argsPrefix: [], resolution: "path", envPatch: {} };
}

