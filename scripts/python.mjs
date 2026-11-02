// Runs a Python command from server/ with the right interpreter, on any OS:
//   $PYTHON if set, else server/.venv if it exists, else the system Python.
// Usage: node scripts/python.mjs -m pytest -q
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const server = join(dirname(fileURLToPath(import.meta.url)), "..", "server");
const windows = process.platform === "win32";
const venvPython = join(server, ".venv", windows ? "Scripts" : "bin", windows ? "python.exe" : "python");
const python = process.env.PYTHON ?? (existsSync(venvPython) ? venvPython : windows ? "py" : "python3");

const result = spawnSync(python, process.argv.slice(2), { cwd: server, stdio: "inherit" });
if (result.error) {
  console.error(`Cannot run "${python}": ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status ?? 1);
