import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { LightsOrder, Zone, ZoneInput } from "../../api/types";
import { useDevices } from "../../hooks/useDevices";
import { useNotice } from "../../hooks/useNotice";
import { CLightsControls } from "../components/CLightsControls";
import { CZoneEditor } from "../components/CZoneEditor";
import { CNotice } from "../subcomponents/display/CNotice";

type Kind = "rooms" | "groups";

export function VZones() {
  const { t } = useTranslation();
  const { notice, show } = useNotice();
  const [kind, setKind] = useState<Kind>("rooms");
  const [zones, setZones] = useState<Record<Kind, Zone[]>>({ rooms: [], groups: [] });
  const { devices } = useDevices(); // live: the buttons and sliders follow the lights
  const [editing, setEditing] = useState<Zone | "new" | null>(null);

  const load = useCallback(async () => {
    try {
      const [rooms, groups] = await Promise.all([api.rooms.list(), api.groups.list()]);
      setZones({ rooms, groups });
    } catch (e) {
      show((e as Error).message, "error");
    }
  }, [show]);

  useEffect(() => {
    load();
  }, [load]);

  async function save(input: ZoneInput) {
    try {
      if (editing && editing !== "new") await api[kind].update(editing.id, input);
      else await api[kind].create(input);
      setEditing(null);
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  async function remove(zone: Zone) {
    if (!window.confirm(t("CONFIRM_DELETE", { name: zone.name }))) return;
    try {
      await api[kind].remove(zone.id);
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  /** One order for a room or a group (zone) or, without one, for the whole home. */
  async function order(lights: LightsOrder, zone?: Zone) {
    try {
      const results = Object.values(zone ? await api[kind].light(zone.id, lights) : await api.lights(lights));
      const ok = results.filter(Boolean).length;
      show(t("SCENE_APPLIED", { ok, total: results.length }), ok === results.length ? "ok" : "error");
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  const deviceName = (id: string) => devices.find((d) => d.id === id)?.name ?? id;
  const list = zones[kind];

  return (
    <div className="page-card">
      <div className="flex flex-wrap justify-between items-center gap-2 px-4 md:px-6 py-2">
        <h2 className="text-2xl">{t("ZONES")}</h2>
        {!editing && (
          <button
            onClick={() => setEditing("new")}
            aria-label={t(kind === "rooms" ? "NEW_ROOM" : "NEW_GROUP")}
            title={t(kind === "rooms" ? "NEW_ROOM" : "NEW_GROUP")}
            className="border-2 border-gray-300 dark:border-gray-600 rounded-full w-10 h-10 text-2xl leading-none hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            +
          </button>
        )}
      </div>

      {!editing && (
        <div className="flex flex-wrap gap-2 px-4 md:px-6" role="tablist">
          {(["rooms", "groups"] as const).map((k) => (
            <button
              key={k}
              role="tab"
              aria-selected={kind === k}
              onClick={() => setKind(k)}
              className={`px-4 py-1 rounded-full border-2 ${kind === k ? "border-gray-400 bg-gray-200 dark:bg-gray-700" : "border-transparent"}`}
            >
              {t(k === "rooms" ? "ROOMS" : "GROUPS")}
            </button>
          ))}
        </div>
      )}

      {!editing && devices.some((d) => d.capabilities.includes("on_off")) && (
        <div className="mx-4 mt-3 flex flex-wrap items-center gap-2 border-2 border-gray-500 rounded-lg p-4 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900">
          <span className="flex-grow min-w-0 text-lg font-semibold truncate">{t("WHOLE_HOME")}</span>
          <CLightsControls devices={devices} onOrder={(lights) => order(lights)} label={t("WHOLE_HOME")} />
        </div>
      )}

      {editing ? (
        <CZoneEditor
          zone={editing === "new" ? null : editing}
          devices={devices}
          otherRooms={kind === "rooms" ? zones.rooms : []}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      ) : list.length === 0 ? (
        <p className="p-8 text-center text-gray-500">{t(kind === "rooms" ? "NO_ROOMS" : "NO_GROUPS")}</p>
      ) : (
        <ul className="flex flex-col space-y-2 p-4">
          {list.map((zone) => (
            <li key={zone.id} className="flex flex-wrap items-center gap-2 border-2 border-gray-500 rounded-lg p-4 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900">
              <span className="flex-grow min-w-0">
                <span className="block text-lg font-semibold truncate">{zone.name}</span>
                <span className="block text-sm text-gray-500 truncate">
                  {zone.device_ids.length === 0 ? t("DEVICES_COUNT", { count: 0 }) : zone.device_ids.map(deviceName).join(", ")}
                </span>
              </span>
              <span className="flex items-center gap-1 flex-shrink-0">
                <button onClick={() => setEditing(zone)} aria-label={t("EDIT")} title={t("EDIT")} className="px-2">✎</button>
                <button onClick={() => remove(zone)} aria-label={t("DELETE")} title={t("DELETE")} className="px-2 text-red-500">✕</button>
              </span>
              <CLightsControls
                devices={devices.filter((d) => zone.device_ids.includes(d.id))}
                onOrder={(lights) => order(lights, zone)}
                label={zone.name}
              />
            </li>
          ))}
        </ul>
      )}
      <CNotice notice={notice} />
    </div>
  );
}

export default VZones;
