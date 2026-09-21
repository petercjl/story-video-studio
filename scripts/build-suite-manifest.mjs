import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { directoryDigest } from "../src/suite.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const filename = path.join(root, "suite.json");
const suite = JSON.parse(fs.readFileSync(filename, "utf8"));
const skillsRoot = path.join(root, "skills");
const bundled = fs.readdirSync(skillsRoot, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && fs.existsSync(path.join(skillsRoot, entry.name, "SKILL.md")))
  .map((entry) => ({ name: entry.name, ...directoryDigest(path.join(skillsRoot, entry.name)) }))
  .sort((left, right) => left.name.localeCompare(right.name));
const expected = { ...suite, bundled_skills: bundled };
const rendered = `${JSON.stringify(expected, null, 2)}\n`;
if (process.argv.includes("--check")) {
  if (fs.readFileSync(filename, "utf8") !== rendered) {
    process.stderr.write("suite.json is stale; run npm run build:manifest\n");
    process.exitCode = 1;
  }
} else {
  fs.writeFileSync(filename, rendered);
  process.stdout.write(`Recorded ${bundled.length} bundled Skills in suite.json\n`);
}

