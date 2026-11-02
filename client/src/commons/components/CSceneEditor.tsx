import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Device, Scene, SceneAction, SceneInput } from "../../api/types";
import { brightnessToPercent, percentToBrightness } from "../../utils/color";
import { CSlider } from "../subcomponents/actions/CSlider";

type Mode = "none" | "color" | "white";

interface Row {
  included: boolean;
  power: boolean;
  brightness: number | null; // percent, null = leave as is
  mode: Mode;
  color: string;
  kelvin: number;
  fade: number; // seconds to glide to the target, 0 = instant
}

const DEFAULT_ROW: Row = { included: false, power: true, brightness: null, mode: "none", color: "#ffffff", kelvin: 3000, fade: 0 };

export function rowFromAction(action: SceneAction): Row {
  return {
    included: true,
    power: action.power ?? true,
    brightness: action.brightness != null ? brightnessToPercent(action.brightness) : null,
    mode: action.hex_color ? "color" : action.color_temp_kelvin ? "white" : "none",
    color: action.hex_color ?? DEFAULT_ROW.color,
    kelvin: action.color_temp_kelvin ?? DEFAULT_ROW.kelvin,
    fade: action.transition_time ?? 0,
  };
}

export function rowFromDevice(device: Device): Row | null {
  const { state } = device;
  if (state.power == null) return null;
  return {
    included: true,
    power: state.power,
    brightness: state.brightness != null ? brightnessToPercent(state.brightness) : null,
    mode: state.color_temp_kelvin ? "white" : state.hex_color ? "color" : "none",
    color: state.hex_color ?? DEFAULT_ROW.color,
    kelvin: state.color_temp_kelvin ?? DEFAULT_ROW.kelvin,
    fade: 0,
  };
}

export function actionFromRow(device: Device, row: Row): SceneAction {
  const action: SceneAction = { device_id: device.id, power: row.power };
  if (!row.power) return action;
  if (row.brightness != null && device.capabilities.includes("brightness")) {
    action.brightness = percentToBrightness(row.brightness);
  }
  if (row.mode === "color" && device.capabilities.includes("color")) action.hex_color = row.color;
  if (row.mode === "white" && device.capabilities.includes("color_temp")) action.color_temp_kelvin = row.kelvin;
  if (row.fade > 0 && (action.hex_color || action.color_temp_kelvin || action.brightness != null)) {
    action.transition_time = row.fade;
  }
  return action;
}

export interface CSceneEditorProps {
  scene: Scene | null;
  devices: Device[];
  onSave: (scene: SceneInput) => void;
  onCancel: () => void;
}

/** Create/edit a scene: pick the devices and the state each one must reach. */
export function CSceneEditor({ scene, devices, onSave, onCancel }: CSceneEditorProps) {
  const { t } = useTranslation();
  const controllable = devices.filter((d) => d.capabilities.includes("on_off"));
  const [name, setName] = useState(scene?.name ?? "");
  const [rows, setRows] = useState<Record<string, Row>>(() => {
    const initial: Record<string, Row> = {};
    scene?.actions.forEach((a) => (initial[a.device_id] = rowFromAction(a)));
    return initial;
  });

  const rowOf = (id: string): Row => rows[id] ?? DEFAULT_ROW;
  const update = (id: string, patch: Partial<Row>) => setRows((r) => ({ ...r, [id]: { ...rowOf(id), ...patch } }));

  function capture() {
    const captured: Record<string, Row> = {};
    controllable.forEach((d) => {
      const row = rowFromDevice(d);
      if (row) captured[d.id] = row;
    });
    setRows(captured);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const actions = controllable.filter((d) => rowOf(d.id).included).map((d) => actionFromRow(d, rowOf(d.id)));
    if (!name.trim() || actions.length === 0) return;
    onSave({ name: name.trim(), actions });
  }

  const input = "bg-gray-200 dark:bg-gray-700 rounded p-2";

  return (
    <form onSubmit={submit} className="space-y-4 p-4 max-w-xl w-full mx-auto overflow-y-auto">
      <label className="block text-sm">
        {t("NAME")}
        <input required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={`${input} w-full`} />
      </label>

      <button type="button" onClick={capture} className="border-2 border-gray-400 rounded-full px-4 py-1 text-sm hover:bg-gray-200 dark:hover:bg-gray-700">
        {t("CAPTURE_STATE")}
      </button>

      <ul className="space-y-2">
        {controllable.map((d) => {
          const row = rowOf(d.id);
          const caps = d.capabilities;
          return (
            <li key={d.id} className={`border-2 rounded-lg p-3 space-y-2 ${row.included ? "border-gray-400" : "border-gray-700 opacity-70"}`}>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={row.included} onChange={(e) => update(d.id, { included: e.target.checked })} />
                <span className="font-semibold truncate">{d.name}</span>
              </label>
              {row.included && (
                <div className="space-y-2 pl-6">
                  <label className="flex items-center gap-2 text-sm">
                    <input type="checkbox" checked={row.power} onChange={(e) => update(d.id, { power: e.target.checked })} />
                    {row.power ? t("ON") : t("OFF")}
                  </label>
                  {row.power && caps.includes("brightness") && (
                    <label className="flex items-center gap-2 text-sm">
                      {t("BRIGHTNESS")}
                      <CSlider
                        min={1}
                        max={100}
                        value={row.brightness ?? 100}
                        onChange={(e) => update(d.id, { brightness: Number(e.target.value) })}
                        valueLabel={row.brightness != null ? `${row.brightness}%` : "—"}
                        className="w-full max-w-[11rem]"
                      />
                    </label>
                  )}
                  {row.power && (caps.includes("color") || caps.includes("color_temp")) && (
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <select aria-label={t("COLOR")} value={row.mode} onChange={(e) => update(d.id, { mode: e.target.value as Mode })} className={input}>
                        <option value="none">{t("KEEP")}</option>
                        {caps.includes("color") && <option value="color">{t("COLOR")}</option>}
                        {caps.includes("color_temp") && <option value="white">{t("WHITE")}</option>}
                      </select>
                      {row.mode === "color" && (
                        <input type="color" aria-label={t("COLOR")} value={row.color} onChange={(e) => update(d.id, { color: e.target.value })} />
                      )}
                      {row.mode === "white" && (
                        <>
                          <CSlider
                            aria-label={t("WHITE")}
                            min={d.color_temp_range_kelvin?.[0] ?? 2000}
                            max={d.color_temp_range_kelvin?.[1] ?? 6500}
                            step={50}
                            value={row.kelvin}
                            onChange={(e) => update(d.id, { kelvin: Number(e.target.value) })}
                            valueLabel={`${row.kelvin} K`}
                            className="w-full max-w-[11rem]"
                          />
                        </>
                      )}
                    </div>
                  )}
                  {row.power && (row.mode !== "none" || row.brightness != null) && (
                    <label className="flex items-center gap-2 text-sm">
                      {t("FADE")}
                      <input
                        type="number"
                        min={0}
                        max={600}
                        step={0.5}
                        value={row.fade}
                        onChange={(e) => update(d.id, { fade: Math.max(0, Math.min(600, Number(e.target.value) || 0)) })}
                        className={`${input} w-24`}
                      />
                      <span>{t("SECONDS_SHORT")}</span>
                      <span className="text-xs text-gray-500">{row.fade === 0 ? t("FADE_INSTANT") : ""}</span>
                    </label>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} className="px-4 py-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700">
          {t("CANCEL")}
        </button>
        <button type="submit" className="border-2 border-gray-400 rounded-full px-6 py-2 hover:bg-gray-200 dark:hover:bg-gray-700">
          {t("SAVE")}
        </button>
      </div>
    </form>
  );
}
