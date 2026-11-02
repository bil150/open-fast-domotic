// Guided setup of a development environment: checks the tools, installs the client and the
// server dependencies, finds the Zigbee dongle and writes .env.local.
//
//   npm run setup                  asks the few questions
//   npm run setup -- --yes         no question, takes the detected values
//   npm run setup -- --force       rewrite an existing .env.local
//   npm run setup -- --skip-install   only the settings
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { createInterface } from "node:readline/promises";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const server = join(root, "server");
const args = new Set(process.argv.slice(2));
const windows = process.platform === "win32";
const interactive = process.stdin.isTTY && !args.has("--yes");

const title = (text) => console.log(`\n== ${text}`);
function fail(message) {
  console.error(`\nSetup failed: ${message}`);
  process.exit(1);
}
function run(command, commandArgs, options = {}) {
  return spawnSync(command, commandArgs, { stdio: "inherit", shell: windows && command === "npm", ...options });
}

// --- tools --------------------------------------------------------------------------------------
function checkNode() {
  const major = Number(process.versions.node.split(".")[0]);
  if (major < 20) fail(`Node 20 or newer is required (found ${process.versions.node}).`);
  console.log(`ok  Node ${process.versions.node}`);
}

function findPython() {
  const candidates = windows ? ["py", "python"] : ["python3.13", "python3.12", "python3", "python"];
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["-c", "import sys; print('%d.%d' % sys.version_info[:2]); sys.exit(sys.version_info < (3, 12))"], {
      encoding: "utf8",
    });
    if (result.status === 0) {
      console.log(`ok  Python ${result.stdout.trim()} (${candidate})`);
      return candidate;
    }
  }
  return fail("Python 3.12 or newer is required, it was not found.");
}

// --- dongle -------------------------------------------------------------------------------------
/** How much a port name looks like a Zigbee dongle (the usual USB-serial chips). */
const dongleScore = (label) =>
  /CP210|Silicon Labs|CH340|CH910|FTDI|ZBDongle|Zigbee/i.test(label) ? 2 : /USB/i.test(label) ? 1 : 0;

/** Serial ports that look like a Zigbee dongle, best guess first. */
function detectPorts() {
  const ports = [];
  if (windows) {
    const script =
      "[Console]::OutputEncoding = [Text.Encoding]::UTF8; Get-CimInstance Win32_PnPEntity | Where-Object { $_.Name -match '\\(COM\\d+\\)' } | ForEach-Object { $_.Name }";
    const result = spawnSync("powershell", ["-NoProfile", "-Command", script], { encoding: "utf8" });
    for (const line of (result.stdout ?? "").split(/\r?\n/)) {
      const port = /\((COM\d+)\)/.exec(line)?.[1];
      if (port) ports.push({ port, label: line.trim() });
    }
    ports.sort((a, b) => dongleScore(b.label) - dongleScore(a.label));
  } else if (existsSync("/dev")) {
    for (const name of readdirSync("/dev")) {
      if (/^(ttyUSB|ttyACM|cu\.usbserial|cu\.usbmodem)/.test(name)) ports.push({ port: `/dev/${name}`, label: `/dev/${name}` });
    }
  }
  return ports;
}

async function chooseDongle(rl) {
  const ports = detectPorts();
  if (ports.length === 0) {
    console.log("No serial port found: is the dongle plugged in (and its driver installed)?");
    return rl ? ((await rl.question(`Dongle port [${windows ? "COM4" : "/dev/ttyUSB0"}]: `)).trim() || (windows ? "COM4" : "/dev/ttyUSB0")) : windows ? "COM4" : "/dev/ttyUSB0";
  }
  ports.forEach((p, i) => console.log(`  ${i + 1}) ${p.label}`));
  const first = ports[0].port;
  if (!rl) {
    console.log(`Using ${first}`);
    return first;
  }
  const answer = (await rl.question(`Which one is the dongle? [1 = ${first}, or type a port]: `)).trim();
  if (!answer) return first;
  return ports[Number(answer) - 1]?.port ?? answer;
}

// --- steps --------------------------------------------------------------------------------------
async function writeEnv() {
  title("Settings (.env.local)");
  const envPath = join(root, ".env.local");
  if (existsSync(envPath) && !args.has("--force")) {
    console.log(".env.local already exists: kept (use --force to rewrite it).");
    return;
  }
  const rl = interactive ? createInterface({ input: process.stdin, output: process.stdout }) : null;
  const port = await chooseDongle(rl);
  rl?.close();
  const example = readFileSync(join(root, ".env.local.example"), "utf8");
  writeFileSync(envPath, example.replace(/^Z_DONGLE_PATH=.*$/m, `Z_DONGLE_PATH=${port}`));
  console.log(`Written: .env.local (Z_DONGLE_PATH=${port})`);
}

function installDependencies(python) {
  title("Client dependencies");
  if (run("npm", ["--prefix", "client", "install"], { cwd: root }).status !== 0) fail("npm install (client).");

  title("Server: virtual environment and dependencies");
  const venvPython = join(server, ".venv", windows ? "Scripts" : "bin", windows ? "python.exe" : "python");
  if (run(python, ["-m", "venv", ".venv"], { cwd: server }).status !== 0) fail("creating server/.venv.");
  if (run(venvPython, ["-m", "pip", "install", "--quiet", "-r", "requirements-dev.txt"], { cwd: server }).status !== 0) {
    fail("pip install (server).");
  }
  console.log("Installed in server/.venv");
}

// --- main ---------------------------------------------------------------------------------------
title("Tools");
checkNode();
const python = findPython();
if (!args.has("--skip-install")) installDependencies(python);
await writeEnv();

title("Done");
console.log("npm run dev       start the server and the client");
console.log("npm run check     lint, types and tests");
console.log("npm run build     everything, down to the zip in build/");
