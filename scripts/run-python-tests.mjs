import path from "node:path";
import { fileURLToPath } from "node:url";
import { runInherited } from "../src/process.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
for (const relative of ["skills/story-development-director/scripts", "skills/story-video-project-studio/scripts"]) {
  const result = await runInherited("python3", ["-B", "-m", "unittest", "discover", "-s", path.join(root, relative), "-p", "test_*.py"], { cwd: root });
  if (result.code !== 0) process.exit(result.code);
}
