import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Scene, Schedule, ScheduleInput } from "../../api/types";
import { buildCron, parseCron } from "../../utils/cron";

// display order: Monday first, values follow cron (0 = Sunday)
const WEEK = [1, 2, 3, 4, 5, 6, 0];

export interface CScheduleEditorProps {
  schedule: Schedule | null;
  scenes: Scene[];
  onSave: (schedule: ScheduleInput) => void;
  onCancel: () => void;
}

export function CScheduleEditor({ schedule, scenes, onSave, onCancel }: CScheduleEditorProps) {
  const { t } = useTranslation();
  const simple = schedule ? parseCron(schedule.cron) : { time: "07:00", days: [0, 1, 2, 3, 4, 5, 6] };

  const [name, setName] = useState(schedule?.name ?? "");
  const [sceneId, setSceneId] = useState<number | "">(schedule?.scene_id ?? scenes[0]?.id ?? "");
  const [enabled, setEnabled] = useState(schedule?.enabled ?? true);
  const [advanced, setAdvanced] = useState(simple === null);
  const [time, setTime] = useState(simple?.time ?? "07:00");
  const [days, setDays] = useState<number[]>(simple?.days ?? []);
  const [rawCron, setRawCron] = useState(schedule?.cron ?? "0 7 * * *");

  const toggleDay = (day: number) =>
    setDays((current) => (current.includes(day) ? current.filter((d) => d !== day) : [...current, day]));

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || sceneId === "") return;
    const cron = advanced ? rawCron.trim() : buildCron({ time, days });
    onSave({ name: name.trim(), cron, scene_id: sceneId, enabled });
  }

  const input = "bg-gray-200 dark:bg-gray-700 rounded p-2";

  return (
    <form onSubmit={submit} className="space-y-4 p-4 max-w-xl w-full mx-auto">
      <label className="block text-sm">
        {t("NAME")}
        <input required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={`${input} w-full`} />
      </label>
      <label className="block text-sm">
        {t("SCENE")}
        <select required value={sceneId} onChange={(e) => setSceneId(Number(e.target.value))} className={`${input} w-full`}>
          {scenes.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      </label>

      {advanced ? (
        <label className="block text-sm">
          {t("CRON_EXPRESSION")}
          <input value={rawCron} onChange={(e) => setRawCron(e.target.value)} className={`${input} w-full font-mono`} placeholder="30 7 * * 1-5" />
          <span className="text-xs text-gray-500">{t("CRON_HINT")}</span>
        </label>
      ) : (
        <>
          <label className="block text-sm">
            {t("TIME")}
            <input type="time" required value={time} onChange={(e) => setTime(e.target.value)} className={`${input} w-full`} />
          </label>
          <fieldset className="text-sm">
            <legend>{t("DAYS")}</legend>
            <div className="flex flex-wrap gap-2 mt-1">
              {WEEK.map((day) => (
                <button
                  type="button"
                  key={day}
                  aria-pressed={days.includes(day)}
                  onClick={() => toggleDay(day)}
                  className={`px-3 py-1 rounded-full border-2 ${days.includes(day) ? "bg-gray-500 text-white border-gray-500" : "border-gray-400"}`}
                >
                  {t(`DAY_${day}`)}
                </button>
              ))}
            </div>
            <span className="text-xs text-gray-500">{days.length === 0 ? t("EVERY_DAY") : ""}</span>
          </fieldset>
        </>
      )}

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        {t("ENABLED")}
      </label>
      <button
        type="button"
        onClick={() => setAdvanced(!advanced)}
        className="text-xs underline text-gray-500"
      >
        {advanced ? t("SIMPLE_MODE") : t("ADVANCED_MODE")}
      </button>

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
