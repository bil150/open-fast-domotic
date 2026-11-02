// A fade test for one light, to find out where a stutter comes from. Run it while the server is running:
//
//   npm run fade-test -- <device id>          (the ids are listed when none is given)
//   npm run fade-test -- <device id> --dry    (only print what would be sent)
//
// It plays the same change of color in four ways. Watch the light and note which ones are smooth:
//   1. ONE command, a single long fade: what the light does by itself.
//   2. The same fade cut in steps along the hue (what a slow animated scene sends).
//   3. A loop like the animations: a new command every 2 s, each fade lasting 2 s.
//   4. The same loop with a short pause before each command (never cuts a fade).

import { createInterface } from "node:readline/promises";

const args = process.argv.slice(2);
const dry = args.includes("--dry");
const deviceId = args.find((a) => !a.startsWith("--"));
const api = `${process.env.API_URL ?? "http://localhost:8000"}/api/v1`;

const sleep = (seconds) => new Promise((resolve) => setTimeout(resolve, seconds * 1000));

async function call(path, init) {
  const response = await fetch(`${api}${path}`, { headers: { "Content-Type": "application/json" }, ...init }).catch(
    () => {
      console.error(`Cannot reach the server at ${api}. Start it with "npm run dev" (or set API_URL).`);
      process.exit(1);
    }
  );
  if (!response.ok) throw new Error(`${init?.method ?? "GET"} ${path}: ${response.status} ${await response.text()}`);
  return response.json();
}

if (!deviceId) {
  const { devices } = await call("/devices");
  console.log("Give the id of a light:\n");
  for (const d of devices.filter((d) => d.capabilities.includes("color"))) console.log(`  ${d.id}   ${d.name}`);
  process.exit(0);
}

const light = (hex, seconds) => {
  console.log(`   -> ${hex} over ${seconds} s`);
  if (dry) return Promise.resolve();
  return call(`/devices/${encodeURIComponent(deviceId)}/light`, {
    method: "PATCH",
    body: JSON.stringify({ power: true, brightness: 254, hex_color: hex, transition_time: seconds }),
  });
};

// colors: a deep blue and a pale one, the hardest change to make gently
const DEEP = "#0000ff";
const PALE = "#ffffcc";

function hsv([r, g, b]) {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  const h = d === 0 ? 0 : max === r ? ((g - b) / d + 6) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h / 6, max === 0 ? 0 : d / max];
}
const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
function toHex(h, s) {
  const i = Math.floor(h * 6);
  const f = h * 6 - i;
  const [p, q, t] = [1 - s, 1 - f * s, 1 - (1 - f) * s];
  const c = [[1, t, p], [q, 1, p], [p, 1, t], [p, q, 1], [t, p, 1], [1, p, q]][i % 6];
  return "#" + c.map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("");
}
/** `n` points from `a` to `b`: the hue turns the short way, the saturation changes evenly. */
function path(a, b, n) {
  const [ha, sa] = hsv(rgb(a));
  const [hb, sb] = hsv(rgb(b));
  const arc = ((hb - ha + 0.5) % 1) - 0.5;
  return Array.from({ length: n }, (_, i) => {
    const t = (i + 1) / n;
    return i === n - 1 ? b : toHex((ha + arc * t + 1) % 1, sa + (sb - sa) * t);
  });
}

const rl = createInterface({ input: process.stdin, output: process.stdout });
const ask = async (text) => (dry ? "" : rl.question(`\n${text}\n   (Enter to start) `));

console.log(`Light: ${deviceId}${dry ? "  (dry run)" : ""}`);
console.log("Put the light where you can see it well. Each test starts from the deep blue.\n");

async function reset() {
  console.log(" reset to deep blue");
  await light(DEEP, 2);
  await sleep(dry ? 0 : 4);
}

await ask("TEST 1 - ONE command: a single 6 s fade from deep blue to pale yellow, then back.");
await reset();
await light(PALE, 6);
await sleep(dry ? 0 : 7);
await light(DEEP, 6);
await sleep(dry ? 0 : 7);

await ask("TEST 2 - the same 6 s fade cut in 3 steps of 2 s along the hue, then back.");
await reset();
for (const hex of path(DEEP, PALE, 3)) {
  await light(hex, 2);
  await sleep(dry ? 0 : 2);
}
for (const hex of path(PALE, DEEP, 3)) {
  await light(hex, 2);
  await sleep(dry ? 0 : 2);
}

await ask("TEST 3 - a loop like an animated scene: a command every 2 s, each fade lasting 2 s (6 changes).");
await reset();
for (let i = 0; i < 6; i++) {
  await light(i % 2 === 0 ? PALE : DEEP, 2);
  await sleep(dry ? 0 : 1.9); // the next command goes out a little before the fade ends
}
await sleep(dry ? 0 : 2);

await ask("TEST 4 - the same loop, but each command waits until the fade is over (2 s fade, command every 2.3 s).");
await reset();
for (let i = 0; i < 6; i++) {
  await light(i % 2 === 0 ? PALE : DEEP, 2);
  await sleep(dry ? 0 : 2.3);
}

rl.close();
console.log(`
Which tests were smooth?
  1 smooth, 3 not   -> the loop of the server is at fault: send me the result of 3 and 4.
  1 not smooth      -> the light itself does not fade that change well: 2 shows whether cutting it in steps helps.
  4 smooth, 3 not   -> cutting a fade short with the next command is what makes it jump.
`);
