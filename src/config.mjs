import fs from "node:fs";
import path from "node:path";
import { configPath } from "./paths.mjs";

const defaults = {
  settings: {
    auto_update: true,
    update_check_hours: 6,
    update_registry: "auto"
  }
};

export function loadConfig() {
  try {
    const parsed = JSON.parse(fs.readFileSync(configPath(), "utf8"));
    return { settings: { ...defaults.settings, ...(parsed.settings || {}) } };
  } catch {
    return structuredClone(defaults);
  }
}

export function saveConfig(config) {
  const filename = configPath();
  fs.mkdirSync(path.dirname(filename), { recursive: true, mode: 0o700 });
  const temporary = `${filename}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(config, null, 2)}\n`, { mode: 0o600 });
  fs.renameSync(temporary, filename);
  try { fs.chmodSync(filename, 0o600); } catch {}
  return filename;
}

