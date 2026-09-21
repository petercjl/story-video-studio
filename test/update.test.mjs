import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { isNewerVersion, maybeAutoUpdate } from "../src/update.mjs";

test("semantic version comparison detects newer releases", () => {
  assert.equal(isNewerVersion("0.2.0", "0.1.9"), true);
  assert.equal(isNewerVersion("0.1.0", "0.1.0"), false);
  assert.equal(isNewerVersion("0.0.9", "0.1.0"), false);
});

test("six-hour freshness gate skips a registry lookup", async () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-fresh-"));
  const state = path.join(temporary, "state.json");
  const now = Date.now();
  fs.writeFileSync(state, JSON.stringify({ last_checked_at: now - 60_000, latest: "0.1.0" }));
  let calls = 0;
  const result = await maybeAutoUpdate(["preflight"], { name: "@example/story", version: "0.1.0" }, {
    env: {}, stateFile: state, now: () => now, sourceCheckout: false,
    loadConfig: () => ({ settings: { auto_update: true, update_check_hours: 6 } }),
    run: async () => { calls += 1; return { code: 0, stdout: "", stderr: "" }; }
  });
  assert.equal(result.reason, "fresh");
  assert.equal(calls, 0);
});

test("new release installs, requests managed Skill refresh, and reexecutes once", async () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-update-"));
  const calls = [];
  let inherited = null;
  const result = await maybeAutoUpdate(["preflight", "--agent", "sealseek", "--json"], { name: "@example/story", version: "0.1.0" }, {
    env: {}, stateFile: path.join(temporary, "state.json"), lockFile: path.join(temporary, "lock"), sourceCheckout: false,
    loadConfig: () => ({ settings: { auto_update: true, update_check_hours: 6 } }),
    managedAgents: () => ["sealseek"],
    run: async (command, args) => {
      calls.push([command, ...args]);
      if (args[0] === "config") return { code: 0, stdout: "https://registry.npmjs.org/\n", stderr: "" };
      if (args[0] === "view") return { code: 0, stdout: '"0.2.0"\n', stderr: "" };
      return { code: 0, stdout: "installed", stderr: "" };
    },
    runInherited: async (command, args, options) => { inherited = { command, args, env: options.env }; return { code: 0 }; }
  });
  assert.equal(result.updated, true);
  assert.deepEqual(calls.at(-1), ["npm", "install", "--global", "@example/story@latest", "--registry", "https://registry.npmjs.org/"]);
  assert.equal(inherited.env.STORY_VIDEO_STUDIO_REFRESH_AGENTS, "sealseek");
  assert.equal(inherited.env.STORY_VIDEO_STUDIO_AUTO_UPDATE_GUARD, "1");
});

test("registry failure warns and leaves the verified local release usable", async () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-offline-"));
  const result = await maybeAutoUpdate(["preflight"], { name: "@example/story", version: "0.1.0" }, {
    env: {}, stateFile: path.join(temporary, "state.json"), sourceCheckout: false,
    loadConfig: () => ({ settings: { auto_update: true, update_check_hours: 6 } }),
    run: async () => ({ code: 1, stdout: "", stderr: "offline" })
  });
  assert.match(result.warning, /Unable to check npm for updates/);
});

test("failed refresh restores the previous package and managed Skill suite", async () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "story-video-studio-rollback-"));
  const installs = [];
  const inherited = [];
  await assert.rejects(() => maybeAutoUpdate(["preflight", "--agent", "codex"], { name: "@example/story", version: "0.1.0" }, {
    env: {}, stateFile: path.join(temporary, "state.json"), lockFile: path.join(temporary, "lock"), sourceCheckout: false,
    loadConfig: () => ({ settings: { auto_update: true, update_check_hours: 6 } }),
    managedAgents: () => ["codex", "sealseek"],
    run: async (command, args) => {
      if (args[0] === "config") return { code: 0, stdout: "https://registry.npmjs.org/\n", stderr: "" };
      if (args[0] === "view") return { code: 0, stdout: '"0.2.0"\n', stderr: "" };
      installs.push(args[2]);
      return { code: 0, stdout: "installed", stderr: "" };
    },
    runInherited: async (_command, args, options) => {
      inherited.push({ args, refresh: options.env.STORY_VIDEO_STUDIO_REFRESH_AGENTS });
      return { code: inherited.length === 1 ? 1 : 0 };
    }
  }), (error) => error.code === "UPDATE_REFRESH_FAILED" && error.details.rollback_ok && error.details.rollback_refresh_ok);
  assert.deepEqual(installs, ["@example/story@latest", "@example/story@0.1.0"]);
  assert.equal(inherited.length, 2);
  assert.equal(inherited[1].refresh, "codex,sealseek");
  assert.deepEqual(inherited[1].args.slice(-2), ["version", "--json"]);
});
