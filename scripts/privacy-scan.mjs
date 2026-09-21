import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ignored = new Set([".git", "node_modules", "coverage"]);
const findings = [];
const patterns = [
  ["private-key", /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/],
  ["github-token", /\bgh[opusr]_[A-Za-z0-9_]{20,}\b/],
  ["openai-key", /\bsk-[A-Za-z0-9_-]{20,}\b/],
  ["bearer-token", /Bearer\s+[A-Za-z0-9._-]{20,}/i],
  ["credential-assignment", /(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*["'][^"']{8,}["']/i],
  ["author-home", /\/Users\/pechen(?:\/|\b)/],
  ["windows-user-home", /[A-Za-z]:\\Users\\(?:pechen|Peter)(?:\\|\b)/i],
  ["private-skill", /qiushi-ai-script-director|qiushi-e-handoff|秋拾/iu]
];

function inspect(filename) {
  const relative = path.relative(root, filename);
  if (relative === "scripts/privacy-scan.mjs") return;
  if (/\.(png|jpe?g|gif|webp|mp4|mov|wav|mp3|xlsx|zip)$/i.test(filename)) return;
  const content = fs.readFileSync(filename, "utf8");
  for (const [rule, pattern] of patterns) {
    const match = content.match(pattern);
    if (match) findings.push({ rule, file: relative, match: match[0].slice(0, 80) });
  }
  if (/\.before-|\.backup-|\.pytest_cache|__pycache__/.test(relative)) findings.push({ rule: "development-artifact", file: relative });
}

function walk(current) {
  for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
    if (ignored.has(entry.name)) continue;
    const absolute = path.join(current, entry.name);
    if (entry.isDirectory()) walk(absolute);
    else if (entry.isFile()) inspect(absolute);
  }
}

walk(root);
if (findings.length) {
  process.stderr.write(`${JSON.stringify({ ok: false, findings }, null, 2)}\n`);
  process.exitCode = 1;
} else {
  process.stdout.write(`${JSON.stringify({ ok: true, scanned_root: ".", findings: [] }, null, 2)}\n`);
}

