import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { api, streamUrl } from "../../api/client";
import { Device } from "../../api/types";
import { createThrottle } from "../../hooks/useThrottledCallback";
import { useNotice } from "../../hooks/useNotice";
import { createBeatDetector, levelToBrightness, rmsLevel, smoothLevel } from "../../utils/audio";
import { CNotice } from "../subcomponents/display/CNotice";

type Source = "mic" | "system";

const SEND_EVERY_MS = 40; // upper bound; the server keeps only the newest value when the radio is busy
const MIN_STEP = 3; // brightness changes smaller than this are not worth a radio message
const MAX_COLORS = 6;
const DEFAULT_COLOR = "#ff00ff";
const DEFAULT_COLORS = [DEFAULT_COLOR];

async function openStream(source: Source): Promise<MediaStream> {
  if (source === "mic") return navigator.mediaDevices.getUserMedia({ audio: true });
  // browsers insist on a video track to share a tab or screen; only its audio is used
  const stream = await navigator.mediaDevices.getDisplayMedia({ audio: true, video: true });
  stream.getVideoTracks().forEach((track) => track.stop());
  if (stream.getAudioTracks().length === 0) {
    stream.getTracks().forEach((track) => track.stop());
    throw new Error("NO_AUDIO_SHARED");
  }
  return stream;
}

function openSocket(): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(streamUrl());
    socket.onopen = () => resolve(socket);
    socket.onerror = () => reject(new Error("STREAM_UNAVAILABLE"));
  });
}

/** Music mode: the lights follow the loudness of the microphone or of the system sound,
 *  and step through their own colors on each beat. */
export function CMusicPanel() {
  const { t } = useTranslation();
  const { notice, show } = useNotice();
  const [lights, setLights] = useState<Device[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [palettes, setPalettes] = useState<Record<string, string[]>>({});
  const [source, setSource] = useState<Source>("mic");
  const [sensitivity, setSensitivity] = useState(3);
  const [running, setRunning] = useState(false);
  const [level, setLevel] = useState(0);
  const stopRef = useRef<(() => void) | null>(null);
  const settings = useRef({ selected, sensitivity, palettes });

  useEffect(() => {
    settings.current = { selected, sensitivity, palettes };
  }, [selected, sensitivity, palettes]);

  useEffect(() => {
    api.devices
      .list()
      .then((devices) => setLights(devices.filter((d) => d.capabilities.includes("brightness"))))
      .catch((e: Error) => show(e.message, "error"));
  }, [show]);

  const stop = useCallback(() => {
    stopRef.current?.();
    stopRef.current = null;
    setRunning(false);
    setLevel(0);
  }, []);

  useEffect(() => stop, [stop]);

  const paletteOf = (id: string) => palettes[id] ?? DEFAULT_COLORS;
  const setPalette = (id: string, colors: string[]) => setPalettes((current) => ({ ...current, [id]: colors }));

  async function start() {
    if (selected.length === 0) return show(t("MUSIC_PICK_LIGHT"), "error");
    if (!navigator.mediaDevices) return show(t("MUSIC_NEEDS_HTTPS"), "error");
    let stream: MediaStream | null = null;
    let socket: WebSocket | null = null;
    try {
      stream = await openStream(source);
      socket = await openSocket();
      const context = new AudioContext({ latencyHint: "interactive" });
      const analyser = context.createAnalyser();
      analyser.fftSize = 512;
      analyser.smoothingTimeConstant = 0;
      context.createMediaStreamSource(stream).connect(analyser);
      const samples = new Uint8Array(analyser.fftSize);

      // each light starts on its first color (and is switched on); after that everything goes through the socket
      const colorIndex = new Map(selected.map((id, i) => [id, i])); // lights start out of step
      const colorOf = (id: string) => {
        const palette = settings.current.palettes[id] ?? DEFAULT_COLORS;
        return palette[(colorIndex.get(id) ?? 0) % palette.length] ?? DEFAULT_COLOR;
      };
      selected.forEach((id) => api.devices.light(id, { power: true, hex_color: colorOf(id) }).catch(() => undefined));

      const pendingColor = new Map<string, string>(); // a color change must not be lost by the throttle
      let lastBrightness = 0;
      let lastSent = -MIN_STEP;
      const send = createThrottle((brightness: number) => {
        if (socket?.readyState !== WebSocket.OPEN) return;
        const moved = Math.abs(brightness - lastSent) >= MIN_STEP || brightness === 5 || brightness === 255;
        if (!moved && pendingColor.size === 0) return;
        lastSent = brightness;
        lastBrightness = brightness;
        settings.current.selected.forEach((id) => {
          const message: { device_id: string; brightness: number; hex_color?: string } = { device_id: id, brightness };
          const color = pendingColor.get(id);
          if (color) message.hex_color = color;
          socket?.send(JSON.stringify(message));
        });
        pendingColor.clear();
      }, SEND_EVERY_MS);

      const isBeat = createBeatDetector();
      let smoothed = 0;
      let frame = requestAnimationFrame(function tick(now) {
        analyser.getByteTimeDomainData(samples);
        smoothed = smoothLevel(smoothed, rmsLevel(samples), 1, 0.25);
        setLevel(smoothed);
        const { sensitivity: gain, selected: ids, palettes: all } = settings.current;
        if (isBeat(Math.min(1, smoothed * gain), now)) {
          ids.forEach((id) => {
            if ((all[id] ?? DEFAULT_COLORS).length < 2) return;
            colorIndex.set(id, (colorIndex.get(id) ?? 0) + 1);
            pendingColor.set(id, colorOf(id));
          });
        }
        send(levelToBrightness(smoothed, gain));
        frame = requestAnimationFrame(tick);
      });

      const openedStream = stream;
      const openedSocket = socket;
      openedStream.getAudioTracks()[0]?.addEventListener("ended", stop);
      openedSocket.onclose = stop;
      stopRef.current = () => {
        cancelAnimationFrame(frame);
        send.cancel();
        openedSocket.onclose = null;
        openedSocket.close();
        openedStream.getTracks().forEach((track) => track.stop());
        void context.close();
        // the fast path does not update the server's idea of each light: say where they ended up
        settings.current.selected.forEach((id) =>
          api.devices.light(id, { brightness: Math.max(1, lastBrightness) }).catch(() => undefined)
        );
      };
      setRunning(true);
    } catch (e) {
      stream?.getTracks().forEach((track) => track.stop());
      socket?.close();
      const message = (e as Error).message;
      show(
        message === "NO_AUDIO_SHARED" ? t("MUSIC_NO_AUDIO") : message === "STREAM_UNAVAILABLE" ? t("MUSIC_STREAM_FAILED") : message,
        "error"
      );
    }
  }

  const toggleLight = (id: string) =>
    setSelected((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));

  return (
    <div className="flex flex-col gap-4 p-4">
      <h3 className="text-xl">{t("MUSIC_MODE")}</h3>
      <p className="text-sm text-gray-500">{t("MUSIC_HINT")}</p>

      <fieldset className="flex gap-4" disabled={running}>
        {(["mic", "system"] as const).map((s) => (
          <label key={s} className="flex items-center gap-2">
            <input type="radio" name="music-source" checked={source === s} onChange={() => setSource(s)} />
            {t(s === "mic" ? "MUSIC_SOURCE_MIC" : "MUSIC_SOURCE_SYSTEM")}
          </label>
        ))}
      </fieldset>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1">{t("DEVICES")}</legend>
        {lights.length === 0 && <span className="text-gray-500">{t("NO_DEVICES")}</span>}
        {lights.map((d) => {
          const canColor = d.capabilities.includes("color");
          const colors = paletteOf(d.id);
          return (
            <div key={d.id} className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 min-w-[8rem]">
                <input type="checkbox" checked={selected.includes(d.id)} onChange={() => toggleLight(d.id)} disabled={running} />
                {d.name}
              </label>
              {canColor && selected.includes(d.id) && (
                <span className="flex items-center gap-1" aria-label={t("MUSIC_COLORS")}>
                  {colors.map((color, i) => (
                    <span key={i} className="flex items-center">
                      <input
                        type="color"
                        value={color}
                        onChange={(e) => setPalette(d.id, colors.map((c, j) => (j === i ? e.target.value : c)))}
                      />
                      {colors.length > 1 && (
                        <button
                          onClick={() => setPalette(d.id, colors.filter((_, j) => j !== i))}
                          aria-label={t("MUSIC_REMOVE_COLOR")}
                          title={t("MUSIC_REMOVE_COLOR")}
                          className="px-1 text-red-500"
                        >
                          ✕
                        </button>
                      )}
                    </span>
                  ))}
                  {colors.length < MAX_COLORS && (
                    <button
                      onClick={() => setPalette(d.id, [...colors, "#00ffff"])}
                      aria-label={t("MUSIC_ADD_COLOR")}
                      title={t("MUSIC_ADD_COLOR")}
                      className="border-2 border-gray-400 rounded-full w-7 h-7 leading-none hover:bg-gray-200 dark:hover:bg-gray-700"
                    >
                      +
                    </button>
                  )}
                </span>
              )}
            </div>
          );
        })}
      </fieldset>

      <label className="flex items-center gap-3">
        {t("MUSIC_SENSITIVITY")}
        <input type="range" min={1} max={10} step={0.5} value={sensitivity} onChange={(e) => setSensitivity(Number(e.target.value))} />
      </label>

      <div className="h-3 rounded-full bg-gray-300 dark:bg-gray-700 overflow-hidden" aria-hidden>
        <div className="h-full bg-gray-500" style={{ width: `${Math.min(1, level * sensitivity) * 100}%` }} />
      </div>

      <button
        onClick={running ? stop : start}
        className="self-start border-2 border-gray-400 rounded-full px-6 py-1 hover:bg-gray-200 dark:hover:bg-gray-700"
      >
        {running ? t("MUSIC_STOP") : t("MUSIC_START")}
      </button>
      <CNotice notice={notice} />
    </div>
  );
}
