import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { Scene, Schedule, ScheduleInput } from "../../api/types";
import { useNotice } from "../../hooks/useNotice";
import { describeCron } from "../../utils/cron";
import { CScheduleEditor } from "../components/CScheduleEditor";
import { CMusicPanel } from "../components/CMusicPanel";
import { CNotice } from "../subcomponents/display/CNotice";

const TAB_LABELS = { schedules: "SCHEDULES_DAILY", music: "MUSIC_MODE" } as const;

export function VAutomations() {
  const { t } = useTranslation();
  const { notice, show } = useNotice();
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [editing, setEditing] = useState<Schedule | "new" | null>(null);
  const [tab, setTab] = useState<"schedules" | "music">("schedules");

  const load = useCallback(async () => {
    try {
      const [loadedSchedules, loadedScenes] = await Promise.all([api.schedules.list(), api.scenes.list()]);
      setSchedules(loadedSchedules);
      setScenes(loadedScenes);
    } catch (e) {
      show((e as Error).message, "error");
    }
  }, [show]);

  useEffect(() => {
    load();
  }, [load]);

  const dayNames = [0, 1, 2, 3, 4, 5, 6].map((d) => t(`DAY_${d}`));
  const sceneName = (id: number) => scenes.find((s) => s.id === id)?.name ?? `#${id}`;

  async function save(input: ScheduleInput) {
    try {
      if (editing && editing !== "new") await api.schedules.update(editing.id, input);
      else await api.schedules.create(input);
      setEditing(null);
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  async function toggle(schedule: Schedule) {
    try {
      await api.schedules.update(schedule.id, {
        name: schedule.name,
        cron: schedule.cron,
        scene_id: schedule.scene_id,
        enabled: !schedule.enabled,
      });
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  async function remove(schedule: Schedule) {
    if (!window.confirm(t("CONFIRM_DELETE", { name: schedule.name }))) return;
    try {
      await api.schedules.remove(schedule.id);
      await load();
    } catch (e) {
      show((e as Error).message, "error");
    }
  }

  return (
    <div className="page-card">
      <div className="flex flex-wrap justify-between items-center gap-2 px-4 md:px-6 py-2">
        <h2 className="text-2xl">{t("AUTOMATIONS")}</h2>
        {tab === "schedules" && !editing && scenes.length > 0 && (
          <button
            onClick={() => setEditing("new")}
            aria-label={t("NEW_SCHEDULE")}
            title={t("NEW_SCHEDULE")}
            className="border-2 border-gray-300 dark:border-gray-600 rounded-full w-10 h-10 text-2xl leading-none hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            +
          </button>
        )}
      </div>

      {!editing && (
        <div role="tablist" className="flex flex-wrap gap-2 px-4 md:px-6 pb-2 text-sm">
          {(["schedules", "music"] as const).map((name) => (
            <button
              key={name}
              role="tab"
              aria-selected={tab === name}
              onClick={() => setTab(name)}
              className={`px-4 py-1 rounded-full border-2 ${tab === name ? "bg-gray-500 text-white border-gray-500" : "border-gray-400"}`}
            >
              {t(TAB_LABELS[name])}
            </button>
          ))}
        </div>
      )}

      {tab === "music" && !editing ? (
        <CMusicPanel />
      ) : editing ? (
        <CScheduleEditor
          schedule={editing === "new" ? null : editing}
          scenes={scenes}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
      ) : schedules.length === 0 ? (
        <p className="p-8 text-center text-gray-500">{scenes.length === 0 ? t("SCHEDULE_NEEDS_SCENE") : t("NO_SCHEDULES")}</p>
      ) : (
        <ul className="flex flex-col space-y-2 p-4">
          {schedules.map((schedule) => (
            <li key={schedule.id} className={`flex items-center justify-between gap-2 border-2 border-gray-500 rounded-lg p-4 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900 ${schedule.enabled ? "" : "opacity-60"}`}>
              <span className="min-w-0">
                <span className="block text-lg font-semibold truncate">{schedule.name}</span>
                <span className="block text-sm">{describeCron(schedule.cron, dayNames, t("EVERY_DAY"))}</span>
                <span className="block text-sm text-gray-500 truncate">
                  {sceneName(schedule.scene_id)}
                  {schedule.next_run && ` · ${t("NEXT_RUN")}: ${schedule.next_run.replace("T", " ")}`}
                </span>
              </span>
              <span className="flex items-center gap-1 flex-shrink-0">
                <input type="checkbox" aria-label={t("ENABLED")} checked={schedule.enabled} onChange={() => toggle(schedule)} />
                <button onClick={() => setEditing(schedule)} aria-label={t("EDIT")} title={t("EDIT")} className="px-2">✎</button>
                <button onClick={() => remove(schedule)} aria-label={t("DELETE")} title={t("DELETE")} className="px-2 text-red-500">✕</button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <CNotice notice={notice} />
    </div>
  );
}

export default VAutomations;
