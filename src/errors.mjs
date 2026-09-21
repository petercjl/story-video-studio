export class CliError extends Error {
  constructor(code, message, details = null) {
    super(message);
    this.name = "CliError";
    this.code = code;
    this.details = details;
  }
}

export function requireValue(value, code, message) {
  if (value === undefined || value === null || value === "") throw new CliError(code, message);
  return value;
}

