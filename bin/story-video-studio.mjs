#!/usr/bin/env node
import { main } from "../src/cli.mjs";
import { CliError } from "../src/errors.mjs";

const json = process.argv.includes("--json");
try {
  await main(process.argv.slice(2));
} catch (error) {
  const normalized = error instanceof CliError
    ? error
    : new CliError("UNEXPECTED_ERROR", error?.message || String(error));
  const payload = { ok: false, error: { code: normalized.code, message: normalized.message, details: normalized.details || null } };
  if (json) process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
  else process.stderr.write(`[${normalized.code}] ${normalized.message}\n`);
  process.exitCode = 1;
}

