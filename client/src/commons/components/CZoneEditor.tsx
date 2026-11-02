import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Device, Zone, ZoneInput } from "../../api/types";

export interface CZoneEditorProps {
  zone: Zone | null;
  devices: Device[];
  /** For a room: the other rooms, to tell which light would be moved here. */
  otherRooms?: Zone[];
  onSave: (zone: ZoneInput) => void;
  onCancel: () => void;
}

/** Create/edit a room or a group: a name and the lights it holds. */
export function CZoneEditor({ zone, devices, otherRooms = [], onSave, onCancel }: CZoneEditorProps) {
  const { t } = useTranslation();
  const lights = devices.filter((d) => d.capabilities.includes("on_off"));
  const [name, setName] = useState(zone?.name ?? "");
  const [selected, setSelected] = useState<Set<string>>(new Set(zone?.device_ids ?? []));

  const toggle = (id: string, on: boolean) =>
    setSelected((current) => {
      const next = new Set(current);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    onSave({ name: name.trim(), device_ids: lights.filter((d) => selected.has(d.id)).map((d) => d.id) });
  }

  const input = "bg-gray-200 dark:bg-gray-700 rounded p-2";
  const roomOf = (id: string) => otherRooms.find((r) => r.id !== zone?.id && r.device_ids.includes(id));

  return (
    <form onSubmit={submit} className="space-y-4 p-4 max-w-xl w-full mx-auto overflow-y-auto">
      <label className="block text-sm">
        {t("NAME")}
        <input required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={`${input} w-full`} />
      </label>

      <fieldset className="space-y-2">
        <legend className="text-sm">{t("ZONE_DEVICES")}</legend>
        <ul className="space-y-1">
          {lights.map((d) => {
            const elsewhere = roomOf(d.id);
            return (
              <li key={d.id}>
                <label className="flex items-center gap-2 border-2 border-gray-500 rounded-lg p-2">
                  <input type="checkbox" checked={selected.has(d.id)} onChange={(e) => toggle(d.id, e.target.checked)} />
                  <span className="truncate">{d.name}</span>
                  {elsewhere && (
                    <span className="ml-auto text-xs text-gray-500" title={t("ZONE_MOVES_HINT")}>
                      {elsewhere.name}
                    </span>
                  )}
                </label>
              </li>
            );
          })}
        </ul>
      </fieldset>

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
