import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { ButtonAction, ButtonMapping, Device, Scene } from "../../api/types";
import { useNotice } from "../../hooks/useNotice";
import { CNotice } from "../subcomponents/display/CNotice";
import { CDeviceProps } from "./CBulbControl";
import { CDeviceHeader } from "./CDeviceHeader";

interface Props extends CDeviceProps {
  allDevices: Device[];
}

type ActionType = ButtonAction["type"];

const field = "bg-gray-200 dark:bg-gray-700 rounded p-2 w-full";

/** Remote/button: the last press, and what each press triggers. */
export function CButtonView({ device, allDevices, onListClick, onDeviceChange }: Props) {
  const { t } = useTranslation();
  const { notice, show } = useNotice();
  const [mappings, setMappings] = useState<ButtonMapping[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);

  const [event, setEvent] = useState(device.state.last_button?.event ?? "");
  const [type, setType] = useState<ActionType>("scene");
  const [sceneId, setSceneId] = useState<number | "">("");
  const [targetId, setTargetId] = useState("");
  const [powerState, setPowerState] = useState(true);

  const controllable = allDevices.filter((d) => d.capabilities.includes("on_off"));

  const load = useCallback(async () => {
    try {
      const [loadedMappings, loadedScenes] = await Promise.all([api.buttons.list(device.id), api.scenes.list()]);
      setMappings(loadedMappings);
      setScenes(loadedScenes);
    } catch (e) {
      show((e as Error).message, "error");
    }
  }, [device.id, show]);

  useEffect(() => {
    load();
  }, [load]);

  // the live "last press" pre-fills the event so a mapping is: press, pick an action, save
  const lastEvent = device.state.last_button?.event;
  useEffect(() => {
    if (lastEvent) setEvent(lastEvent);
  }, [lastEvent]);

  function buildAction(): ButtonAction | null {
    if (type === "scene") return sceneId === "" ? null : { type, scene_id: sceneId };
    if (!targetId) return null;
    return type === "toggle" ? { type, device_id: targetId } : { type, device_id: targetId, state: powerState };
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    const action = buildAction();
    if (!event.trim() || !action) return;
    try {
      await api.buttons.set(device.id, event.trim(), action);
      await load();
    } catch (err) {
      show((err as Error).message, "error");
    }
  }

  async function remove(id: number) {
    try {
      await api.buttons.remove(id);
      await load();
    } catch (err) {
      show((err as Error).message, "error");
    }
  }

  function describe(action: ButtonAction): string {
    const name = (id: string) => allDevices.find((d) => d.id === id)?.name ?? id;
    if (action.type === "scene") return `${t("ACTION_SCENE")}: ${scenes.find((s) => s.id === action.scene_id)?.name ?? action.scene_id}`;
    if (action.type === "toggle") return `${t("ACTION_TOGGLE")}: ${name(action.device_id)}`;
    return `${t("ACTION_POWER")} ${action.state ? t("ON") : t("OFF")}: ${name(action.device_id)}`;
  }

  return (
    <div className="page-card">
      <CDeviceHeader
        device={device}
        onListClick={onListClick}
        onDeviceChange={onDeviceChange}
        onError={(message) => show(message, "error")}
      />
      <div className="p-4 space-y-6 max-w-xl w-full mx-auto">
        <p className="text-center">
          {t("LAST_PRESS")}:{" "}
          <strong>{device.state.last_button?.event ?? t("NO_PRESS_YET")}</strong>
          {device.state.battery != null && <span className="text-gray-500"> · {device.state.battery}%</span>}
        </p>

        <ul className="space-y-2">
          {mappings.map((m) => (
            <li key={m.id} className="flex items-center justify-between gap-2 border-2 border-gray-500 rounded-lg p-3">
              <span className="min-w-0">
                <span className="block font-semibold truncate">{m.event}</span>
                <span className="block text-sm text-gray-500 truncate">{describe(m.action)}</span>
              </span>
              <button aria-label={t("DELETE")} onClick={() => remove(m.id)} className="text-red-500 px-2">
                ✕
              </button>
            </li>
          ))}
        </ul>

        <form onSubmit={save} className="space-y-3">
          <h3 className="text-lg">{t("BUTTON_ACTIONS")}</h3>
          <label className="block text-sm">
            {t("EVENT")}
            <input value={event} onChange={(e) => setEvent(e.target.value)} placeholder="on_off.toggle" className={field} />
          </label>
          <label className="block text-sm">
            {t("ACTION")}
            <select value={type} onChange={(e) => setType(e.target.value as ActionType)} className={field}>
              <option value="scene">{t("ACTION_SCENE")}</option>
              <option value="toggle">{t("ACTION_TOGGLE")}</option>
              <option value="power">{t("ACTION_POWER")}</option>
            </select>
          </label>
          {type === "scene" ? (
            <label className="block text-sm">
              {t("SCENE")}
              <select value={sceneId} onChange={(e) => setSceneId(e.target.value ? Number(e.target.value) : "")} className={field}>
                <option value="" />
                {scenes.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className="block text-sm">
                {t("DEVICE")}
                <select value={targetId} onChange={(e) => setTargetId(e.target.value)} className={field}>
                  <option value="" />
                  {controllable.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </label>
              {type === "power" && (
                <label className="block text-sm">
                  <input type="checkbox" checked={powerState} onChange={(e) => setPowerState(e.target.checked)} /> {t("ON")}
                </label>
              )}
            </>
          )}
          <button type="submit" className="border-2 border-gray-400 rounded-full px-6 py-2 hover:bg-gray-200 dark:hover:bg-gray-700">
            {t("SAVE")}
          </button>
        </form>
      </div>
      <CNotice notice={notice} />
    </div>
  );
}
