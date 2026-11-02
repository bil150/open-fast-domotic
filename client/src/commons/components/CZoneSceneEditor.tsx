import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Device, PaletteColor, Scene, SceneInput, SceneTarget, SPEED_SECONDS, Speed, Zone } from "../../api/types";
import { brightnessToPercent, kelvinToRgb, percentToBrightness, rgbToHex } from "../../utils/color";
import { CSlider } from "../subcomponents/actions/CSlider";

const MAX_COLORS = 16;
const MIN_KELVIN = 2000;
const MAX_KELVIN = 6500;

type Mode = "color" | "white";

interface Swatch {
  mode: Mode;
  color: string;
  kelvin: number;
  brightness: number; // percent
}

const DEFAULT_SWATCH: Swatch = { mode: "color", color: "#ff8800", kelvin: 2700, brightness: 100 };

export function swatchFromColor(color: PaletteColor): Swatch {
  return {
    mode: color.color_temp_kelvin ? "white" : "color",
    color: color.hex_color ?? DEFAULT_SWATCH.color,
    kelvin: color.color_temp_kelvin ?? DEFAULT_SWATCH.kelvin,
    brightness: brightnessToPercent(color.brightness),
  };
}

export function colorFromSwatch(swatch: Swatch): PaletteColor {
  const color: PaletteColor = { brightness: percentToBrightness(swatch.brightness) };
  if (swatch.mode === "white") color.color_temp_kelvin = swatch.kelvin;
  else color.hex_color = swatch.color;
  return color;
}

/** What a color looks like on screen, for the preview pastilles. */
export function cssColor(color: PaletteColor): string {
  return color.hex_color ?? rgbToHex(kelvinToRgb(color.color_temp_kelvin ?? DEFAULT_SWATCH.kelvin));
}

/** Removing a color shifts the ones after it: the lights placed by hand follow their color. */
export function assignmentsAfterRemoval(assignments: Record<string, number>, removed: number): Record<string, number> {
  const next: Record<string, number> = {};
  for (const [id, index] of Object.entries(assignments)) {
    if (index === removed) continue;
    next[id] = index > removed ? index - 1 : index;
  }
  return next;
}

/** A light that takes the colors of the palette. A socket (on/off only) has nothing to color. */
export const takesColors = (device: Device): boolean =>
  ["brightness", "color", "color_temp"].some((capability) => device.capabilities.includes(capability));

/** The same record without one device. */
export function without<T>(record: Record<string, T>, deviceId: string): Record<string, T> {
  return Object.fromEntries(Object.entries(record).filter(([id]) => id !== deviceId));
}

export interface CZoneSceneEditorProps {
  scene: Scene | null;
  rooms: Zone[];
  groups: Zone[];
  devices: Device[];
  onSave: (scene: SceneInput) => void;
  onCancel: () => void;
}

/** Create/edit a scene: a room or a group, the colors spread over its lights, and an optional fade. */
export function CZoneSceneEditor({ scene, rooms, groups, devices, onSave, onCancel }: CZoneSceneEditorProps) {
  const { t } = useTranslation();
  const first: SceneTarget | null = rooms[0]
    ? { type: "room", id: rooms[0].id }
    : groups[0]
      ? { type: "group", id: groups[0].id }
      : null;
  const [name, setName] = useState(scene?.name ?? "");
  const [target, setTarget] = useState<SceneTarget | null>(scene?.target ?? first);
  const [swatches, setSwatches] = useState<Swatch[]>(
    scene?.palette?.length ? scene.palette.map(swatchFromColor) : [DEFAULT_SWATCH]
  );
  const [assignments, setAssignments] = useState<Record<string, number>>(scene?.assignments ?? {});
  const [switches, setSwitches] = useState<Record<string, boolean>>(scene?.switches ?? {});
  const [speed, setSpeed] = useState<Speed>(scene?.speed ?? "medium");
  const [animated, setAnimated] = useState(scene?.animated ?? false);
  const tooFewColors = animated && swatches.length < 2;

  const zones = target?.type === "group" ? groups : rooms;
  const zone = zones.find((z) => z.id === target?.id);
  const switchable = (zone?.device_ids ?? [])
    .map((id) => devices.find((d) => d.id === id))
    .filter((d): d is Device => d !== undefined && d.capabilities.includes("on_off"));
  const lights = switchable.filter(takesColors);
  const sockets = switchable.filter((d) => !takesColors(d));

  const patch = (index: number, change: Partial<Swatch>) =>
    setSwatches((current) => current.map((s, i) => (i === index ? { ...s, ...change } : s)));
  /** An animated scene has one brightness for all its colors (see ANIMATED_SAME_BRIGHTNESS). */
  const setAllBrightness = (brightness: number) => setSwatches((current) => current.map((s) => ({ ...s, brightness })));
  const add = () => setSwatches((current) => [...current, { ...(current[current.length - 1] ?? DEFAULT_SWATCH) }]);
  const remove = (index: number) => {
    setSwatches((current) => current.filter((_, i) => i !== index));
    setAssignments((current) => assignmentsAfterRemoval(current, index));
  };
  /** Put a light on a color of the palette, or switch it off ("off"), or leave it to the automatic spread (""). */
  function place(deviceId: string, value: string) {
    setAssignments((current) => {
      const others = without(current, deviceId);
      return value === "" || value === "off" ? others : { ...others, [deviceId]: Number(value) };
    });
    setSwitches((current) => (value === "off" ? { ...current, [deviceId]: false } : without(current, deviceId)));
  }

  /** A socket is left alone, or switched on, or switched off. */
  const setSocket = (deviceId: string, value: string) =>
    setSwitches((current) => (value === "" ? without(current, deviceId) : { ...current, [deviceId]: value === "on" }));

  function chooseKind(type: SceneTarget["type"]) {
    const list = type === "room" ? rooms : groups;
    if (list[0]) setTarget({ type, id: list[0].id });
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || !target || !zone || swatches.length === 0 || tooFewColors) return;
    const inZone = <T,>(record: Record<string, T>) =>
      Object.fromEntries(Object.entries(record).filter(([id]) => zone.device_ids.includes(id)));
    onSave({
      name: name.trim(),
      target,
      palette: swatches.map(colorFromSwatch),
      assignments: inZone(assignments),
      switches: inZone(switches),
      speed,
      animated,
    });
  }

  const input = "bg-gray-200 dark:bg-gray-700 rounded p-2";
  const palette = swatches.map(colorFromSwatch);

  return (
    <form onSubmit={submit} className="space-y-4 p-4 max-w-xl w-full mx-auto">
      <label className="block text-sm">
        {t("NAME")}
        <input required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={`${input} w-full`} />
      </label>

      <fieldset className="space-y-2">
        <legend className="text-sm">{t("SCENE_TARGET")}</legend>
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label={t("SCENE_TARGET")}
            value={target?.type ?? "room"}
            onChange={(e) => chooseKind(e.target.value as SceneTarget["type"])}
            className={input}
          >
            {rooms.length > 0 && <option value="room">{t("ROOM")}</option>}
            {groups.length > 0 && <option value="group">{t("GROUP")}</option>}
          </select>
          <select
            aria-label={t(target?.type === "group" ? "GROUP" : "ROOM")}
            value={target?.id ?? ""}
            onChange={(e) => target && setTarget({ ...target, id: Number(e.target.value) })}
            className={`${input} flex-grow min-w-0`}
          >
            {!zone && target && <option value={target.id}>{t("ZONE_GONE")}</option>}
            {zones.map((z) => (
              <option key={z.id} value={z.id}>{z.name}</option>
            ))}
          </select>
        </div>
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm">{t("PALETTE")}</legend>
        <div className="flex h-6 rounded-full overflow-hidden border-2 border-gray-500" aria-hidden="true">
          {palette.map((c, i) => (
            <span key={i} className="flex-1" style={{ backgroundColor: cssColor(c) }} />
          ))}
        </div>
        <ol className="space-y-2">
          {swatches.map((s, index) => (
            <li key={index} className="border-2 border-gray-500 rounded-lg p-3 space-y-2">
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span
                  className="w-6 h-6 rounded-full border-2 border-gray-400 flex-shrink-0"
                  style={{ backgroundColor: cssColor(colorFromSwatch(s)) }}
                  aria-hidden="true"
                />
                <span className="font-semibold">{t("COLOR_N", { n: index + 1 })}</span>
                <select
                  aria-label={t("COLOR")}
                  value={s.mode}
                  onChange={(e) => patch(index, { mode: e.target.value as Mode })}
                  className={input}
                >
                  <option value="color">{t("COLOR")}</option>
                  <option value="white">{t("WHITE")}</option>
                </select>
                {s.mode === "color" && (
                  <input type="color" aria-label={t("COLOR")} value={s.color} onChange={(e) => patch(index, { color: e.target.value })} />
                )}
                <button
                  type="button"
                  onClick={() => remove(index)}
                  disabled={swatches.length === 1}
                  aria-label={t("REMOVE_COLOR")}
                  title={t("REMOVE_COLOR")}
                  className="ml-auto px-2 text-red-500 disabled:opacity-30"
                >
                  ✕
                </button>
              </div>
              {s.mode === "white" && (
                <CSlider
                  aria-label={t("WHITE")}
                  min={MIN_KELVIN}
                  max={MAX_KELVIN}
                  step={50}
                  value={s.kelvin}
                  onChange={(e) => patch(index, { kelvin: Number(e.target.value) })}
                  valueLabel={`${s.kelvin} K`}
                  className="w-full max-w-xs"
                />
              )}
              {!animated && (
                <CSlider
                  aria-label={t("BRIGHTNESS")}
                  min={1}
                  max={100}
                  value={s.brightness}
                  onChange={(e) => patch(index, { brightness: Number(e.target.value) })}
                  valueLabel={`${s.brightness}%`}
                  className="w-full max-w-xs"
                />
              )}
            </li>
          ))}
        </ol>
        <button
          type="button"
          onClick={add}
          disabled={swatches.length >= MAX_COLORS}
          className="border-2 border-gray-400 rounded-full px-4 py-1 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          + {t("ADD_COLOR")}
        </button>
      </fieldset>

      <fieldset className="space-y-2">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={animated}
            onChange={(e) => {
              setAnimated(e.target.checked);
              if (e.target.checked) setAllBrightness(swatches[0]?.brightness ?? DEFAULT_SWATCH.brightness);
            }}
          />
          {t("ANIMATED")}
        </label>
        {animated && <p className="text-xs text-gray-500">{t("ANIMATED_HINT")}</p>}
        {animated && swatches[0] && (
          <div className="space-y-1">
            <label className="flex flex-wrap items-center gap-2 text-sm">
              {t("BRIGHTNESS")}
              <CSlider
                aria-label={t("BRIGHTNESS")}
                min={1}
                max={100}
                value={swatches[0].brightness}
                onChange={(e) => setAllBrightness(Number(e.target.value))}
                valueLabel={`${swatches[0].brightness}%`}
                className="w-full max-w-xs"
              />
            </label>
            <p className="text-xs text-gray-500">{t("ANIMATED_SAME_BRIGHTNESS")}</p>
          </div>
        )}
        {tooFewColors && <p role="alert" className="text-sm text-red-500">{t("ANIMATED_NEEDS_TWO")}</p>}
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm">{t("SPEED")}</legend>
        <div role="radiogroup" aria-label={t("SPEED")} className="flex flex-wrap gap-2">
          {(["slow", "medium", "fast"] as const).map((name) => (
            <button
              key={name}
              type="button"
              role="radio"
              aria-checked={speed === name}
              onClick={() => setSpeed(name)}
              className={`px-4 py-1 rounded-full border-2 text-sm ${
                speed === name ? "bg-gray-500 text-white border-gray-500" : "border-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              {t(`SPEED_${name.toUpperCase()}`)} · {SPEED_SECONDS[name]} {t("SECONDS_SHORT")}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500">{t(animated ? "SPEED_HINT_ANIMATED" : "SPEED_HINT")}</p>
      </fieldset>

      {sockets.length > 0 && (
        <fieldset className="space-y-2">
          <legend className="text-sm">{t("SOCKETS")}</legend>
          <p className="text-xs text-gray-500">{t("SOCKETS_HINT")}</p>
          <ul className="space-y-2">
            {sockets.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="truncate min-w-0">{d.name}</span>
                <select
                  aria-label={d.name}
                  value={d.id in switches ? (switches[d.id] ? "on" : "off") : ""}
                  onChange={(e) => setSocket(d.id, e.target.value)}
                  className={input}
                >
                  <option value="">{t("KEEP")}</option>
                  <option value="on">{t("ON")}</option>
                  <option value="off">{t("OFF")}</option>
                </select>
              </li>
            ))}
          </ul>
        </fieldset>
      )}

      {lights.length > 0 && (
        <details className="border-2 border-gray-500 rounded-lg px-3 py-2">
          <summary className="cursor-pointer text-sm font-semibold">{t("PLACE_LIGHTS")}</summary>
          <p className="mt-2 text-xs text-gray-500">{t("PLACE_LIGHTS_HINT")}</p>
          <ul className="mt-2 space-y-2">
            {lights.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="truncate min-w-0">{d.name}</span>
                <select
                  aria-label={d.name}
                  value={switches[d.id] === false ? "off" : (assignments[d.id] ?? "")}
                  onChange={(e) => place(d.id, e.target.value)}
                  className={input}
                >
                  <option value="">{t("AUTO")}</option>
                  {swatches.map((_, i) => (
                    <option key={i} value={i}>{t("COLOR_N", { n: i + 1 })}</option>
                  ))}
                  <option value="off">{t("OFF")}</option>
                </select>
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="px-4 py-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700">
          {t("CANCEL")}
        </button>
        <button type="submit" disabled={!zone || tooFewColors} className="border-2 border-gray-400 rounded-full px-6 py-2 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50">
          {t("SAVE")}
        </button>
      </div>
    </form>
  );
}
