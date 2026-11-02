import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { Device, Scene, SceneInput, Zone } from "../../api/types";
import { useNotice } from "../../hooks/useNotice";
import { CSceneEditor } from "../components/CSceneEditor";
import { CZoneSceneEditor, cssColor } from "../components/CZoneSceneEditor";
import { CNotice } from "../subcomponents/display/CNotice";

export function VScenes() {
  const { t } = useTranslation();
  const { notice, show } = useNotice();
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [rooms, setRooms] = useState<Zone[]>([]);
  const [groups, setGroups] = useState<Zone[]>([]);
  const [editing, setEditing] = useState<Scene | "new" | null>(null);

  const load = useCallback(async () => {
    try {
      const [loadedScenes, loadedDevices, loadedRooms, loadedGroups] = await Promise.all([
        api.scenes.list(),
        api.devices.list(),
        api.rooms.list(),
        api.groups.list(),
      ]);
      setScenes(loadedScenes);
      setDevices(loadedDevices);
      setRooms(loadedRooms);
      setGroups(loadedGroups);
    } catch (e) {
      show((e as Error).message, "error");
    }
  }, [show]);

  useEffect(() => {
    load();
  }, [load]);

  async function save(input: SceneInput) {
    try {
      if (editing && editing !== "new") await api.scenes.update(editing.id, input);
      else await api.scenes.create(input);
      setEditing(null);
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  async function remove(scene: Scene) {
    if (!window.confirm(t("CONFIRM_DELETE", { name: scene.name }))) return;
    try {
      await api.scenes.remove(scene.id);
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  async function apply(scene: Scene) {
    try {
      const results = Object.values(await api.scenes.apply(scene.id));
      const ok = results.filter(Boolean).length;
      show(
        scene.animated ? t("ANIMATED_STARTED") : t("SCENE_APPLIED", { ok, total: results.length }),
        ok === results.length ? "ok" : "error"
      );
      if (scene.animated) await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  async function stop(scene: Scene) {
    try {
      await api.scenes.stop(scene.id);
      show(t("ANIMATED_STOPPED"), "ok");
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  const hasZones = rooms.length + groups.length > 0;
  const zoneOf = (scene: Scene) => (scene.target?.type === "group" ? groups : rooms).find((z) => z.id === scene.target?.id);

  function startNew() {
    if (!hasZones) {
      show(t("SCENE_NEEDS_ZONE"), "error");
      return;
    }
    setEditing("new");
  }

  return (
    <div className="page-card">
      <div className="flex flex-wrap justify-between items-center gap-2 px-4 md:px-6 py-2">
        <h2 className="text-2xl">{t("SCENES")}</h2>
        {!editing && (
          <button
            onClick={startNew}
            aria-label={t("NEW_SCENE")}
            title={t("NEW_SCENE")}
            className="border-2 border-gray-300 dark:border-gray-600 rounded-full w-10 h-10 text-2xl leading-none hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            +
          </button>
        )}
      </div>

      {editing ? (
        editing !== "new" && !editing.target ? (
          <CSceneEditor scene={editing} devices={devices} onSave={save} onCancel={() => setEditing(null)} />
        ) : (
          <CZoneSceneEditor
            scene={editing === "new" ? null : editing}
            rooms={rooms}
            groups={groups}
            devices={devices}
            onSave={save}
            onCancel={() => setEditing(null)}
          />
        )
      ) : scenes.length === 0 ? (
        <p className="p-8 text-center text-gray-500">{hasZones ? t("NO_SCENES") : t("SCENE_NEEDS_ZONE")}</p>
      ) : (
        <ul className="flex flex-col space-y-2 p-4">
          {scenes.map((scene) => {
            const zone = zoneOf(scene);
            return (
              <li key={scene.id} className="flex items-center justify-between gap-2 border-2 border-gray-500 rounded-lg p-4 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900">
                <span className="min-w-0">
                  <span className="block text-lg font-semibold truncate">{scene.name}</span>
                  {scene.target ? (
                    <span className="flex items-center gap-2 text-sm text-gray-500">
                      <span className="flex h-3 w-16 rounded-full overflow-hidden border border-gray-500 flex-shrink-0" aria-hidden="true">
                        {(scene.palette ?? []).map((c, i) => (
                          <span key={i} className="flex-1" style={{ backgroundColor: cssColor(c) }} />
                        ))}
                      </span>
                      <span className="truncate">{zone ? zone.name : t("ZONE_GONE")}</span>
                      {scene.animated && (
                        <span className={`flex-shrink-0 text-xs border rounded-full px-2 ${scene.running ? "border-green-500 text-green-500" : "border-gray-500"}`}>
                          {scene.running ? t("RUNNING") : t("ANIMATED")}
                        </span>
                      )}
                    </span>
                  ) : (
                    <span className="block text-sm text-gray-500">
                      {t("LEGACY_SCENE")} · {t("DEVICES_COUNT", { count: scene.actions.length })}
                    </span>
                  )}
                </span>
                <span className="flex items-center gap-1 flex-shrink-0">
                  {scene.running ? (
                    <button onClick={() => stop(scene)} className="border-2 border-gray-400 rounded-full px-4 py-1 hover:bg-gray-200 dark:hover:bg-gray-700">
                      {t("STOP")}
                    </button>
                  ) : (
                    <button onClick={() => apply(scene)} className="border-2 border-gray-400 rounded-full px-4 py-1 hover:bg-gray-200 dark:hover:bg-gray-700">
                      {t("APPLY")}
                    </button>
                  )}
                  <button onClick={() => setEditing(scene)} aria-label={t("EDIT")} title={t("EDIT")} className="px-2">✎</button>
                  <button onClick={() => remove(scene)} aria-label={t("DELETE")} title={t("DELETE")} className="px-2 text-red-500">✕</button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
      <CNotice notice={notice} />
    </div>
  );
}

export default VScenes;
