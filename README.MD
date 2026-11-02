<h1 align="center">OPEN-FAST-DOMOTIC</h1>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="License: GPL v3"></a>
  <img src="https://img.shields.io/badge/Open%20Source-%E2%9D%A4-brightgreen.svg" alt="Open Source">
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker ready">
</p>

A local hub for a connected home: an HTTP REST API on top of zigpy-znp, with its React client app.

- A lightweight hub for a connected home, simple automation without excess
- Direct communication between a unique coordinator and the devices
- No account, no internet needed
- Open source

A free-time project: the initial motivation is just fun, and building a small intranet application for very basic home automation.


If you need many protocols today, a bigger solution is a better fit. If anybody wants to fork it, do it, please just respect the GPL-3.0 license: a fork stays open source under the same license.

## Features

- **Lights**: on/off, brightness, color and white (color temperature). The client only shows what each bulb supports.
- **Sensors**: temperature and battery, updated live.
- **Buttons**: a button press can apply a scene, toggle a device or switch it on/off.
- **Rooms and groups**: a room is a fixed zone of the home (a light belongs to one room only), a group is any set of lights (a light can be in several). Formed in the client, they are what scenes target. Each room and group has quick buttons to switch all its lights and sockets on or off and to make them brighter or dimmer, and there is a whole-home on/off.
- **Scenes**: pick a room or a group and **one or more colors** (a color or a white, with its brightness). The colors are spread over the lights of the room or group, and a given light can be placed on a given color. Each light keeps only what it can do (a white bulb gets the brightness). A **socket** has no color: in a scene it is set **on**, **off**, or left alone (the default, so that a scene never switches on a kettle or a heater by surprise). A given light can also be set off. The lights always **glide** to their color, at one of **three speeds**: fast (2 s), medium (6 s) or slow (15 s). There is no other time: a glide that is too short for the radio to follow is what makes the lights stutter. Apply a scene from the client, from a button or from a schedule.
- **Animated scenes**: the same palette, but the lights **loop through the colors**, each one starting on a different color, with a fade between them: each color lasts as long as the glide to it (the speed), so the lights glide all the time and never stop on a color and jump to the next. All the colors of an animated scene share **one brightness** (the first color sets it): changing the brightness while the color glides makes many bulbs stutter or skip the glide, so during the animation only the color moves and the level is not sent again. The change from one color to the next is kept **gentle whatever the two colors**: the server cuts it in a few steps so that the hue turns the short way round and the saturation changes evenly (a bulb alone goes straight through its color space, cutting through washed-out colors), and it **never sends anything to a lamp while it is still gliding**: a lamp that receives a second command ends the running glide at once and the color jumps. Each glide ends 0.1 s before the next command goes out, the radio sends one command at a time to a given lamp (in the order they came), and a lit light whose brightness and color both change gets the brightness first and the color after (a light that is off changes color at once, only its brightness glides). It runs on the server, resumes after a restart, and any manual command on one of its lights (or another scene on them) stops it.
- **Automations** (schedules and music mode, in one page). **Schedules**: cron-like automation edited in the client ("07:30 on weekdays"), executed by the server.
- **Sequences** (API): scenes played one after the other, each held for its own duration (A for 2 s, B for 5 s, C for 10 s...), looping or not. With "fade" on, the light glides to the scene and reaches it exactly when the duration ends. The client has no page for them any more: animated scenes do the same job with colors.
- **Quick controls**: on/off, color swatch and brightness slider directly on each device, in a list or in a bento layout. Colors picked in the client are reached with a smooth transition.
- **Music mode**: the lights follow the sound of the microphone or of the system (share a tab or screen with audio). Each bulb can have several colors and steps to the next one on each beat. The colors and brightness go through a dedicated WebSocket that does not wait for the bulbs' answers, to stay close to real time. The browser needs HTTPS or `localhost` to reach the microphone.
- **FX**: a button on each bulb starts a random flicker, wood fire or candle. It runs on the server and any manual command stops it.
- **Live updates**: the client follows the devices through a WebSocket, no refresh needed.
- Light **animations** (color loops) through the API.
- **About** page: a user guide, the project license and the open-source libraries.

## Compatibility

- The system uses zigpy-znp to control coordinators, check the hardware requirements here: https://github.com/zigpy/zigpy-znp
- Any Zigbee device can be paired, whatever its manufacturer. Bulbs, sockets, temperature sensors and buttons are handled.

### Supported devices

A device is recognised by the clusters it announces, not by its model.

| Device | Recognised by | What the client does |
|---|---|---|
| **Light** | on/off + brightness, color or white | on/off, brightness, color, white, rooms, groups, scenes, animated scenes, fades |
| **Socket** | on/off only | on/off, rooms, groups, scenes |
| **Temperature sensor** | temperature measurement cluster | live temperature |
| **Button / remote** | it sends on/off, level or scene commands and has nothing to drive | a press applies a scene, toggles a device or switches it on/off |

Any device that announces a battery cluster also shows its battery level. The signal quality (LQI, RSSI), the last time it was seen and its online state are shown for every device.

**Not handled yet**: motion/presence, door/window, humidity, light-level, water-leak and smoke sensors, blinds, thermostats, locks and sockets that measure power. They can be paired but are listed as "Unknown" without useful values. To add one, open an issue with its model and the log.

**Trademarks**: if a brand, a manufacturer or a model name appears in your system (it is reported by your own devices, not chosen by this project), it belongs to its owner. The owners are entirely independent of this project and hold sole ownership of their products, trademarks and intellectual property. No affiliation or endorsement is implied.

Buttons and sensors have not been verified on every model: if a device does not report, open an issue with its model and the log.
Some bulbs ignore or shorten transitions: if a fade is not smooth on yours, open an issue with its model.

## Installation

Two ways to run open-fast-domotic:

- [**Docker**](#docker) to use it at home (Linux host with the dongle plugged in).
- [**Development**](#development) to work on the code (Windows, Linux or macOS).

In both cases you need a Zigbee coordinator supported by [zigpy-znp](https://github.com/zigpy/zigpy-znp) flashed with the ZNP firmware (see the hardware list of zigpy-znp).

### The dongle

#### Driver

| System | |
|---|---|
| Windows | install the driver of the dongle's USB-to-serial chip (most ZNP dongles use a CP210x), from the maker of your dongle or of the chip |
| Linux | nothing to install on recent kernels. Check with `modinfo cp210x`, load with `sudo modprobe cp210x` |

#### Find its port

| System | How | Looks like |
|---|---|---|
| Windows | Device Manager, "Ports (COM & LPT)" | `COM4` |
| Linux | plug it in, then `ls /dev/ttyUSB* /dev/ttyACM*` | `/dev/ttyUSB0` |

On Linux, your user must be allowed to open it: `sudo usermod -aG dialout $USER`, then log in again. (Docker does not need this, see below.)

> **Only one program can open the dongle at a time.** Stop the server (or the container) before starting another one, or the second one will not find the radio.

### Docker

Requirements: Docker with the compose plugin (**Compose 2.24 or newer**), on a **Linux** host (a small always-on computer, a mini PC, a NAS...) where the dongle is plugged in.

Docker is for the final installation only: in development you do not need it (`npm run dev`).

There are two images, one Dockerfile each, and `docker-compose.yml` ties them together:

| | Dockerfile | What it is |
|---|---|---|
| `server` | `server/Dockerfile` | the Python API. The only one to talk to the dongle and to hold the data |
| `client` | `client/Dockerfile` | nginx serving the built web application, and forwarding `/api` (REST and WebSocket) and `/docs` to the server |

Nothing is compiled inside the images: they pack what `npm run build` produced, which is exactly what is in `build/` (and in the zip). The only published port is the client's: http://localhost:8000.

#### 1. Get the build

Either the zip made by `npm run build` (see [Build system](#build-system)): copy `build/open-fast-domotic-<version>.zip` to the host and unzip it. Or build it on the host: clone the repository, `npm install`, `npm run build`, then `cd build`.

#### 2. Install and start it

```sh
sh install.sh
```

It looks for the dongle, asks for it and for your timezone (**schedules run in this timezone**, the default UTC is probably not what you want), writes `.env`, builds the image and starts it. Options: `--yes` (no question), `--no-docker` (Python virtual environment instead of Docker), `--force` (rewrite `.env`).

The first start takes a few minutes (the image is built on the host).

#### 3. Open it

- App: http://localhost:8000 (or `http://<host ip>:8000` from your phone)
- API documentation: http://localhost:8000/docs

Check the radio started: `sh docker.sh logs`, you should see `Zigbee radio ready`. The status is also on http://localhost:8000/api/v1/coordinator.

#### 4. Pair a device

In the app press **+**, then put the device in pairing mode (bulbs: usually switch on/off 5 times; sockets and sensors: hold their button; see the device's manual). The pairing window stays open 60 seconds, the device appears in the list by itself.

#### Managing it: `docker.sh`

```sh
sh docker.sh help
```

| Command | |
|---|---|
| `up`, `down`, `restart`, `status`, `logs` | start (builds the image), stop (the data is kept), restart, state, follow the log |
| `update` | rebuild the two images after replacing `server/` and `client/` with the ones of a newer build |
| `backup [file.tgz]` | save the data to a file |
| `restore <file.tgz>` | replace the data with a backup (the file must be in this folder) |
| `import-network <app.db>` | start from an existing Zigbee database, to keep the devices you already paired |

#### Your data

Everything the server writes is in the `data` Docker volume (`open-fast-domotic_data`): the Zigbee network key and paired devices (`app.db`), rooms, groups, scenes, schedules and button mappings (`domotic.db`), and the log.

**Back it up** (`sh docker.sh backup`). If `app.db` is lost, the network is formed again and every device must be paired again.

#### Windows hosts: Docker through WSL2

Docker Desktop cannot give a COM port to a container. The way is WSL2 (Linux inside Windows): the USB dongle is attached to WSL, where it becomes `/dev/ttyUSB0`, exactly as on a Linux machine, and the normal `docker-compose.yml` works unchanged. Nothing else is needed (no bridge, no second compose file).

While the dongle is attached to WSL, Windows no longer sees it (no `COM4`): `npm run dev` and Docker cannot use it at the same time.

**Once, to install** (administrator PowerShell):

```powershell
wsl --install -d Ubuntu          # WSL2 and a Linux distribution; skip if you have them (wsl -l -v)
winget install usbipd            # the tool that passes a USB device to WSL; skip if usbipd --version works
```

Docker Desktop must have its WSL integration on for the distribution (Settings, Resources, WSL integration). The CP210x driver is already in the WSL kernel: nothing to install, only to load.

**Share the dongle** (administrator PowerShell, once):

```powershell
usbipd list                      # note the BUSID of the "CP210x USB to UART Bridge (COM4)", e.g. 5-1
usbipd bind --busid 5-1
```

**Each time** you plug the dongle in or restart WSL:

```powershell
usbipd attach --wsl Ubuntu --busid 5-1
```

```sh
# in Ubuntu (WSL)
sudo modprobe cp210x             # loads the driver
ls /dev/ttyUSB0                  # the dongle is there
cd /mnt/d/dev/znp-manager/build  # wherever the build is
docker compose up -d --build
```

To not type the driver line again, put `[boot]` and `command = modprobe cp210x` in `/etc/wsl.conf` of the distribution (a CH340 chip uses `ch341`). To not attach by hand, `usbipd attach --wsl Ubuntu --busid 5-1 --auto-attach` stays running and reattaches the dongle.

On macOS the dongle cannot be given to Docker: use [development mode](#development).

## Development

Requirements: Python 3.12+ and Node 20+. Everything is driven from the repository root with `npm run ...` scripts (Windows, Linux and macOS).

```sh
npm install      # the root tooling (runs both sides together)
npm run setup    # the guided setup, see below
npm run dev
```

`npm run setup` does the whole procedure:

1. checks Node 20+ and Python 3.12+;
2. installs the client dependencies;
3. creates `server/.venv` and installs the server dependencies;
4. looks for the Zigbee dongle (a list of the serial ports, the one that looks like a dongle first), asks which one it is and writes `.env.local`. An existing `.env.local` is kept.

Options: `npm run setup -- --yes` (no question, takes the detected port), `-- --force` (rewrite `.env.local`), `-- --skip-install` (only the settings).

- API: http://localhost:8000 (documentation on http://localhost:8000/docs), reloads when you edit Python files.
- Client: http://localhost:3001 (Vite), reloads when you edit the client. It talks to the API on `http://localhost:8000` (see `.env.development`), the server accepts that origin by default (`CORS_ORIGINS=*`).

The server creates `server/persistence/` (Zigbee database, its own database, log).

No dongle at hand? Start the server with `ENABLE_ZIGBEE=false` (PowerShell: `$env:ENABLE_ZIGBEE="false"`) or use the **Server (no dongle)** launch configuration: the API runs with an empty device list.

### Build system

| Command | |
|---|---|
| `npm run dev` | server + client, with live reload. `dev:server` / `dev:client` for one of them |
| `npm run build` | **everything, in order**: lint + types + tests (client and server), client build, then the `build/` folder with the zip `build/open-fast-domotic-<version>.zip` and its `.sha256`. Stops at the first failure |
| `npm run release` | `build` plus the pre-release gates: the version is the same in `package.json`, `client/package.json` and `server/app/core/config.py`, the git tree is clean, and the zip contains no database, secret, log or cache |
| `npm start` | build the client, then the server serving it on http://localhost:8000: the same thing as the Docker image |
| `npm run lint` | ESLint (client), ruff (server) |
| `npm run typecheck` | `tsc` with every strict flag (client), `mypy --strict` (server) |
| `npm test` | Vitest (client) and pytest (server). No dongle needed: a fake coordinator and fake Zigbee devices |
| `npm run check` | lint + typecheck + test, the whole thing |
| `npm run format` | ruff format (server) |

The scripts use `server/.venv` when it exists, else the system Python (`py` on Windows, `python3` elsewhere). Set the `PYTHON` environment variable to use another interpreter.

#### Options

```sh
npm run build -- --skip-checks     # no lint / types / tests (quick local build)
npm run release -- --allow-dirty   # release with uncommitted changes (to try it)
```

#### Releasing

1. Bump the version in the 3 places (`package.json`, `client/package.json`, `server/app/core/config.py`).
2. Commit.
3. `npm run release`.
4. Publish `build/open-fast-domotic-<version>.zip` and its `.sha256`.

Everything the build produces is in `build/`, and the zip is the same folder packed. It holds what is in the project and nothing else: `server/` (the Python code, `requirements.txt`, its Dockerfile), `client/` (the built web application in `client/dist`), the Docker files (`docker-compose.yml`, `.env.example`, `docker.sh`, and `server/Dockerfile`, `client/Dockerfile`, `client/nginx.conf`), the guided installer `install.sh`, `start.sh` / `start.bat`, and the documentation. Unzip it on the machine that has the dongle and run `sh install.sh`.

### VS Code

`.vscode/tasks.json`: **Ctrl+Shift+B** runs **Build** (checks, client, zip). Other tasks: Build (no checks), Release, Check.

`.vscode/launch.json` has ready-made configurations (F5): **Server**, **Server (no dongle)**, **Server tests**, **Client**, **Client in Chrome**, and the compounds **Server + Client** and **Server (no dongle) + Client**. Select the `server/.venv` interpreter first (Ctrl+Shift+P, "Python: Select Interpreter"). `.vscode/settings.json` makes VS Code use the TypeScript version of the client project.

The client is built with **Vite**. Its tooling configuration is in `client/` (`vite.config.ts`, `tsconfig.json`, `eslint.config.js`), the server's in `server/pyproject.toml`.

### Configuration (`.env`)

One `.env` at the root of the project, read by **docker compose** (loaded as is into the server), by the **server** and by the **client** (Vite) in dev. Copy `.env.example`.

`.env` holds the values shared by every way of running it (the timezone, the baudrate, the host device for Docker). The dongle port is not in it: it is `/dev/ttyUSB0` by default, which is what the container uses, and `.env.local` sets your own. To run the server on your own machine (`npm run dev`), `.env.local` (not committed, written by `npm run setup`, model: `.env.local.example`) holds what differs there: the dongle port. It wins over `.env`. In a container the server keeps its data in `/data` (the volume) by itself; on your machine, in `server/persistence`.

| Variable | Default | |
|---|---|---|
| `Z_DONGLE_PATH` | `/dev/ttyUSB0` | serial port of the dongle |
| `Z_DONGLE_BAUDRATE` | `115200` | |
| `DATA_DIR` | `./persistence` (`/data` in a container) | folder of everything the server writes: databases, log |
| `DB_PATH` | `<DATA_DIR>/app.db` | zigpy database (Zigbee network key + paired devices) |
| `CORS_ORIGINS` | `*` | allowed web origins, comma separated |
| `RESTORE_ANIMATIONS` | `true` | resume running animations, FX, animated scenes and sequences after a restart |
| `STATIC_DIR` | | folder of the built client to serve (set by the Docker image) |

## Project structure

```
.
├── docker-compose.yml                ties the two images together (final installation only)
├── package.json, scripts/            build system (build.mjs, setup.mjs), install.sh, docker.sh
├── client/                           React + TypeScript + Tailwind, built with Vite
│   ├── Dockerfile, nginx.conf            the client image: nginx serving dist/, forwarding /api
│   ├── vite.config.ts, tsconfig.json     Vite, strict TypeScript
│   └── src/
│       ├── api/                      typed REST client (client.ts) and the API types
│       ├── hooks/                    useDevices (list + WebSocket), debounce, notices
│       ├── utils/                    color, cron and audio (loudness, beats) helpers
│       └── commons/
│           ├── view/                 pages: devices, rooms and groups, scenes, automations, settings, about
│           ├── components/           device screens: bulb (with FX), sensor, button, editors, music panel
│           ├── subcomponents/        small controls: color picker, brightness, power
│           └── application/locale/   translations (en, fr, nl, ar)
└── server/
    ├── Dockerfile                    the server image
    ├── app/
    │   ├── main.py                   create_app(): wiring, CORS, errors, serves the client
    │   ├── api/                      HTTP layer: routes only, no logic
    │   │   └── routes/               devices, coordinator, rooms, groups, scenes, schedules, sequences, buttons, ws
    │   ├── schemas/                  Pydantic models: what the API accepts and returns
    │   ├── services/                 business logic
    │   │   ├── hub.py                the one entry point to devices, whatever the protocol
    │   │   └── zones (rooms, groups), scenes, color_path (the gentle way between two colors), schedules, scheduler, sequences, buttons, animations, effects, device_meta
    │   ├── repositories/             database access, one class per table (SQLAlchemy)
    │   ├── models/                   SQLAlchemy tables
    │   ├── db/                       engine, sessions, table creation
    │   ├── protocols/                everything that talks to a radio
    │   │   ├── base.py               BaseCoordinator: the interface a protocol implements
    │   │   └── zigbee/               zigpy-znp implementation
    │   ├── core/                     settings, logging, errors, dependency wiring
    │   └── utils/                    color conversion, cron helpers
    ├── pyproject.toml                pytest, ruff and mypy --strict configuration
    └── tests/                        pytest, fake coordinator, no hardware
```

## Architecture

A request goes through the layers in one direction only:

`api/routes` → `services` → `repositories` (database) and `protocols` (radio)

- **Routes** validate the request with a schema and call a service. They contain no logic.
- **Services** hold the logic. `Hub` is the only one that knows the radios, so scenes, schedules and buttons work with any protocol.
- **Repositories** are the only code that writes SQL. Services own the transactions.
- **Protocols** implement `BaseCoordinator` (`list_devices`, `set_light`, `toggle`, `refresh`, events...). To add a protocol, implement it and register it in `core/container.py`.

## API

Interactive documentation: `/docs`. Main routes, all under `/api/v1`:

| | |
|---|---|
| `GET /devices`, `GET /devices/{id}` | devices with capabilities, online status and state |
| `PATCH /devices/{id}/light` | `power`, `brightness` (0-255), `hex_color` or `hue`+`saturation`, `color_temp_kelvin`, `transition_time` |
| `PATCH /devices/{id}` | rename |
| `POST /devices/{id}/toggle`, `/refresh` | toggle, read fresh values (sensors) |
| `PUT`/`DELETE /devices/{id}/animation` | color loop (`DELETE` also stops a FX) |
| `GET`/`PUT /devices/{id}/effect` | FX on a bulb: `{effect: fire\|candle, brightness}` (the peak), `GET` tells which one runs |
| `POST /coordinator/discovery?seconds=60` | allow pairing, `GET /coordinator` for the radio status |
| `GET/POST /rooms`, `GET/PUT/DELETE /rooms/{id}` | rooms: `{name, device_ids}`. A device is in one room at most: saving a room moves its devices out of the others |
| `GET/POST /groups`, `GET/PUT/DELETE /groups/{id}` | groups: `{name, device_ids}`. A device can be in several groups |
| `PATCH /rooms/{id}/light`, `PATCH /groups/{id}/light` | one order for all the lights and sockets of the room or group: `power`, `brightness` (1-255) or `brightness_step` (percent, negative to dim), `transition_time`. A socket only gets `power`. Answers `{results: {device id: did it acknowledge}}` |
| `PATCH /lights` | the same order for every light and socket of the home (whole-home on/off) |
| `GET/POST /scenes`, `GET/PUT/DELETE /scenes/{id}` | scenes, see [Scenes](#scenes) |
| `POST /scenes/{id}/apply`, `POST /scenes/{id}/stop` | apply a scene (an animated scene starts looping), stop an animated scene |
| `GET/POST /schedules`, `PUT/DELETE /schedules/{id}` | schedules (`cron` has 5 fields) |
| `GET/POST /sequences`, `PUT/DELETE /sequences/{id}` | sequences: `steps` of `{scene_id, duration, fade}`, `loop`, `enabled` (a sequence runs while it is enabled) |
| `GET /buttons`, `PUT /buttons`, `DELETE /buttons/{id}` | what a button event triggers |
| `WS /ws` | `{type: state\|button\|joined\|left, device_id, data}` |
| `WS /stream` | live light for effects such as the music mode: send `{device_id, brightness?, hex_color?}`, the newest value wins and nothing is answered |

A command the device does not acknowledge answers `502`; a command it cannot do (color on a white bulb) answers `422`.

### Scenes

A scene has one of two shapes:

- **Room or group + palette** (what the client creates):

  ```json
  {
    "name": "Warm evening",
    "target": {"type": "room", "id": 1},
    "palette": [{"hex_color": "#ff8800", "brightness": 200}, {"color_temp_kelvin": 2700}],
    "assignments": {"<light id>": 1},
    "switches": {"<socket id>": true, "<other light id>": false},
    "speed": "medium"
  }
  ```

  `speed` is `"fast"` (2 s), `"medium"` (6 s, the default) or `"slow"` (15 s): how long the lights take to glide to their color. It is the only way to set a time, whatever the scene; the scene answers with the seconds it stands for in `fade` and `duration`. A scene saved before there were three speeds keeps working: an animation is never played with a glide shorter than 2 s. `palette` has 1 to 16 colors (an animated scene gives all of them the brightness of the first), each a `hex_color` or a `color_temp_kelvin`, with an optional `brightness` (0-255). Light number *i* of the room or group gets color *i* (then it starts over); `assignments` (device id -> palette index) places a light on a given color. `switches` (device id -> `true` on / `false` off) gives a state to the sockets, which have no color, and switches off the lights listed with `false` (they take no color of the palette). A socket that is not listed is left as it is. The devices are looked up when the scene is applied, so a scene follows the lights added to or removed from its room or group. A light only gets what it can do.

- **Animated**: the same, plus `"animated": true` and `"duration"` (at least two colors). The speed is the time each color lasts, and the glide from one color to the next lasts that whole time. Light *i* starts on color *i* and every light moves one color further every `duration` seconds, so they are never all the same at once. Between two colors a light glides along a path worked out by the server (a few intermediate points, 2 s at least apart and 4 at most per change), not along the straight line a bulb would take: the hue turns the short way round and the saturation changes evenly, the level staying the same all along. A glide shorter than 4 s is one plain fade, and no step is ever shorter than 2 s. The same rule holds for a plain scene: brightness first, color after, each taking half of the fade. On a light that does color, a white of the palette is shown as a color when the palette also has colors, because a bulb cannot glide between a color and a white temperature without a jump. The `switches` are applied once, when the loop starts. `POST /scenes/{id}/apply` starts the loop, `POST /scenes/{id}/stop` ends it, and `running` in the scene tells whether it runs. A command on one of its lights from anywhere else (a person, a button, another scene) stops it.

- **Per device** (the older shape, still accepted): `"actions": [{"device_id", "power", "brightness", "hex_color", ..., "transition_time"}]`.

Sequences and schedules apply scenes, whichever shape they have.

A server updated from an older version keeps its data: the new columns are added to the existing tables at startup.

### Buttons

Press the button, open it in the client: its last event (e.g. `on_off.toggle`) is shown and pre-filled, pick what it triggers and save.
Battery buttons and sensors sleep: if one does not report, press its button, then use Refresh.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `GET /api/v1/coordinator` says `"ready": false` | the dongle is not found or busy. Check `last_error` there, the port in `.env` / `Z_DONGLE_DEVICE`, and that no other program (another server, a serial terminal) holds it. The server retries every 30 s by itself |
| Devices stay "Not responding", log shows `MAC_NO_ACK` | the device is off, unplugged, out of range or was removed from the network. Nothing to fix in the software |
| A sensor or button shows no value | battery devices sleep. Press their button, then use **Refresh** in the app. A button also needs a press before its events can be mapped |
| The glides of an animated scene stop and start, or a light jumps | the radio takes too long to deliver the commands (look for `a step took ... s to be acknowledged` in the log). Put fewer lights in the scene, choose a slower speed, or move the dongle (a USB extension cable away from the computer and from Wi-Fi helps). A few bulbs ignore or shorten transitions, which no software can fix |
| A fade is not smooth and you do not know why | `npm run fade-test -- <device id>` (the ids are listed when none is given) plays the same change of color four ways on one light: a single long fade, the same fade cut in steps, and a loop like an animated scene with and without cutting each fade short. Compare which ones are smooth: it tells whether the light, the steps or the loop is at fault |
| A schedule runs at the wrong hour | set `TZ` (Docker) or check the server's clock and timezone |
| "Live updates disconnected" in the app | the WebSocket dropped (server restarting?). It reconnects every 3 s |
| `pip` (or `python`) is not recognized on Windows | Python was installed without "Add to PATH", only the `py` launcher exists. Use `npm run setup` (it finds Python itself), or `py -m pip install -r requirements-dev.txt` |
| "Unsupported upgrade request" / the WebSocket answers 404 | the server dependencies are out of date (no WebSocket library). Run `npm run setup` again |
| Every device must be paired again | `app.db` was lost or the volume was recreated. Restore your backup |
| `sh docker.sh up` cannot find `/dev/ttyUSB0` | the dongle is on another port (`ls /dev/ttyUSB* /dev/ttyACM*`), set `Z_DONGLE_DEVICE` |

### Talking to the dongle directly

`zigpy-cli` drives the radio without the server (stop the server first, the port can only be opened once). Replace `COM4` with your port:

```sh
pip install zigpy-cli
zigpy -v radio znp COM4 info                          # firmware and network information
zigpy -v radio znp COM4 permit                        # open pairing
zigpy -v radio znp COM4 backup network.json           # save the network (it holds the network key: keep it private)
zigpy -v radio znp COM4 form                          # form a new network
zigpy -v radio znp COM4 reset                         # reset the radio
python -m zigpy_znp.tools.nvram_reset COM4            # total reset of the dongle: every device must be paired again
```

## Contributing

Forking is welcome. To contribute directly, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Copyright (C) 2026 @bil150. Open-Fast-Domotic is free software, released under the [GNU General Public License v3.0](LICENSE): you can use, study, modify and share it, and if you share it, modified or not, it stays under the same license with its source available.

It builds on [zigpy](https://github.com/zigpy/zigpy) and [zigpy-znp](https://github.com/zigpy/zigpy-znp), which are GPL-3.0 too. The licenses of the other libraries are listed in [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt) and in the About page.
