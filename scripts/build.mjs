// One command for everything. Everything it produces is in build/.
//
//   npm run build     tests/lint/types first, then the client, then build/ and the zip
//   npm run release   the same, preceded by the pre-release gates (versions, clean git tree)
//                     and followed by an audit of the zip content
//
// Options: --skip-checks (no lint/types/tests),
//          --allow-dirty (release only: accept uncommitted changes)
import AdmZip from "adm-zip";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const args = new Set(process.argv.slice(2));
const release = args.has("--release");
const out = join(root, "build");

const readJson = (path) => JSON.parse(readFileSync(join(root, path), "utf8"));
const version = readJson("package.json").version;
const archiveName = `open-fast-domotic-${version}.zip`;
const archive = join(out, archiveName);

/** What goes into build/, as [path in the project, path in build/]. Nothing else is shipped. */
const FILES = [
  // Docker, used for the final installation only: one image for the server, one for the client
  ["docker-compose.yml", "docker-compose.yml"],
  [".env.example", ".env.example"],
  ["server/Dockerfile", "server/Dockerfile"],
  ["server/.dockerignore", "server/.dockerignore"],
  ["client/Dockerfile", "client/Dockerfile"],
  ["client/nginx.conf", "client/nginx.conf"],
  ["client/.dockerignore", "client/.dockerignore"],
  // how to install and run it
  ["scripts/install.sh", "install.sh"],
  ["scripts/docker.sh", "docker.sh"],
  ["scripts/start.sh", "start.sh"],
  ["scripts/start.bat", "start.bat"],
  // the server
  ["server/requirements.txt", "server/requirements.txt"],
  // documentation
  ["README.MD", "README.MD"],
  ["CONTRIBUTING.md", "CONTRIBUTING.md"],
  ["CODE_OF_CONDUCT.md", "CODE_OF_CONDUCT.md"],
  ["LICENSE", "LICENSE"],
];

function fail(message) {
  console.error(`\n${release ? "Release" : "Build"} failed: ${message}`);
  process.exit(1);
}

function step(title, command) {
  console.log(`\n=== ${title}`);
  const started = Date.now();
  if (spawnSync(command, { cwd: root, stdio: "inherit", shell: true }).status !== 0) fail(title);
  console.log(`--- ${title}: ${((Date.now() - started) / 1000).toFixed(1)} s`);
}

// --- pre-release gates --------------------------------------------------------------------------
function gates() {
  console.log("\n=== Pre-release gates");

  const serverVersion = /version:\s*str\s*=\s*"([^"]+)"/.exec(readFileSync(join(root, "server/app/core/config.py"), "utf8"))?.[1];
  const versions = {
    "package.json": version,
    "client/package.json": readJson("client/package.json").version,
    "server/app/core/config.py": serverVersion,
  };
  const mismatched = Object.entries(versions).filter(([, v]) => v !== version);
  if (mismatched.length) {
    fail(`versions differ (expected ${version}): ${mismatched.map(([file, v]) => `${file}=${v}`).join(", ")}`);
  }
  console.log(`ok  version ${version} is the same in the 3 places`);

  const git = spawnSync("git status --porcelain", { cwd: root, shell: true, encoding: "utf8" });
  if (git.status === 0 && git.stdout.trim() && !args.has("--allow-dirty")) {
    const lines = git.stdout.trim().split("\n");
    fail(`uncommitted changes (${lines.length}), commit them first or use --allow-dirty:\n${lines.slice(0, 10).join("\n")}${lines.length > 10 ? "\n..." : ""}`);
  }
  console.log(git.stdout.trim() ? "ok  uncommitted changes allowed (--allow-dirty)" : "ok  git tree is clean");
}

// --- audit of the archive -----------------------------------------------------------------------
const FORBIDDEN = /(\.db(-shm|-wal)?|\.env|\.log(\.\d+)?|\.pyc|\.pem|\.key)$|__pycache__|node_modules|\.venv|persistence\//;

function audit() {
  console.log("\n=== Archive audit");
  const entries = new AdmZip(archive).getEntries().map((e) => e.entryName);
  const forbidden = entries.filter((name) => FORBIDDEN.test(name));
  if (forbidden.length) fail(`the archive contains files that must not be shipped:\n${forbidden.join("\n")}`);
  const required = [...FILES.map(([, to]) => to), "server/app/main.py", "client/dist/index.html"];
  const missing = required.filter((name) => !entries.includes(name));
  if (missing.length) fail(`the archive misses: ${missing.join(", ")}`);
  console.log(`ok  ${entries.length} files, no database, secret, log or cache, every expected file present`);
}

// --- pipeline -----------------------------------------------------------------------------------
if (release) gates();

if (!args.has("--skip-checks")) {
  step("Checks: lint, types and tests (client and server)", "npm run check");
}

step("Client: type-check and production build", "npm run build:client");

console.log("\n=== Assemble build/");
rmSync(out, { recursive: true, force: true });
mkdirSync(out, { recursive: true });
cpSync(join(root, "server", "app"), join(out, "server", "app"), {
  recursive: true,
  filter: (source) => !source.includes("__pycache__"),
});
cpSync(join(root, "client", "dist"), join(out, "client", "dist"), { recursive: true }); // the built client
for (const [from, to] of FILES) {
  cpSync(join(root, from), join(out, to));
}
console.log(`Written: ${out}`);

console.log("\n=== Archive");
const zip = new AdmZip();
zip.addLocalFolder(out); // the zip does not exist yet: it does not contain itself
zip.writeZip(archive);
const sha256 = createHash("sha256").update(readFileSync(archive)).digest("hex");
writeFileSync(`${archive}.sha256`, `${sha256}  ${archiveName}\n`);
console.log(`Written: ${archive}\n         sha256 ${sha256}`);

if (release) audit();

console.log(`\n${release ? "Release" : "Build"} done: ${archive}`);
