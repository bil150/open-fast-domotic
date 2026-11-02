import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../api/client";
import { Scene, Sequence, SequenceInput } from "../../api/types";
import { useNotice } from "../../hooks/useNotice";
import { CNotice } from "../subcomponents/display/CNotice";
import { CSequenceEditor } from "./CSequenceEditor";

/** "Red 2 s → Green 5 s → Blue 10 s" */
export function describeSteps(sequence: Sequence, sceneName: (id: number) => string, seconds: string): string {
  return sequence.steps.map((s) => `${sceneName(s.scene_id)} ${s.duration} ${seconds}`).join(" → ");
}

/** The sequences tab of the schedules view: list, create, edit, start/stop. */
export function CSequencesPanel() {
  const { t } = useTranslation();
  const { notice, show } = useNotice();
  const [sequences, setSequences] = useState<Sequence[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [editing, setEditing] = useState<Sequence | "new" | null>(null);

  const load = useCallback(async () => {
    // independent, so that a failing list does not hide the other (and the + button)
    const [loadedSequences, loadedScenes] = await Promise.allSettled([api.sequences.list(), api.scenes.list()]);
    if (loadedScenes.status === "fulfilled") setScenes(loadedScenes.value);
    if (loadedSequences.status === "fulfilled") setSequences(loadedSequences.value);
    const failure = [loadedSequences, loadedScenes].find((r) => r.status === "rejected");
    if (failure?.status === "rejected") show((failure.reason as Error).message, "error");
  }, [show]);

  useEffect(() => {
    load();
  }, [load]);

  const sceneName = (id: number) => scenes.find((s) => s.id === id)?.name ?? `#${id}`;

  async function attempt(action: () => Promise<unknown>) {
    try {
      await action();
      await load();
      return true;
    } catch (e) {
      show((e as Error).message, "error");
      return false;
    }
  }

  async function save(input: SequenceInput) {
    const saved = await attempt(() =>
      editing && editing !== "new" ? api.sequences.update(editing.id, input) : api.sequences.create(input)
    );
    if (saved) setEditing(null);
  }

  const toggle = (s: Sequence) =>
    attempt(() => api.sequences.update(s.id, { name: s.name, steps: s.steps, loop: s.loop, enabled: !s.enabled }));

  async function remove(s: Sequence) {
    if (!window.confirm(t("CONFIRM_DELETE", { name: s.name }))) return;
    await attempt(() => api.sequences.remove(s.id));
  }

  if (editing) {
    return (
      <>
        <CSequenceEditor
          sequence={editing === "new" ? null : editing}
          scenes={scenes}
          onSave={save}
          onCancel={() => setEditing(null)}
        />
        <CNotice notice={notice} />
      </>
    );
  }

  return (
    <>
      <div className="flex justify-end px-6">
        {scenes.length > 0 && (
          <button
            onClick={() => setEditing("new")}
            aria-label={t("NEW_SEQUENCE")}
            title={t("NEW_SEQUENCE")}
            className="border-2 border-gray-300 dark:border-gray-600 rounded-full w-10 h-10 text-2xl leading-none hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            +
          </button>
        )}
      </div>
      {sequences.length === 0 ? (
        <p className="p-8 text-center text-gray-500">{scenes.length === 0 ? t("SCHEDULE_NEEDS_SCENE") : t("NO_SEQUENCES")}</p>
      ) : (
        <ul className="flex flex-col space-y-2 p-4">
          {sequences.map((sequence) => (
            <li
              key={sequence.id}
              className={`flex items-center justify-between gap-2 border-2 border-gray-500 rounded-lg p-4 bg-gradient-to-r dark:from-gray-700 dark:to-gray-900 ${sequence.enabled ? "" : "opacity-60"}`}
            >
              <span className="min-w-0">
                <span className="block text-lg font-semibold truncate">
                  {sequence.running && <span className="text-green-500" aria-label={t("RUNNING")}>▶ </span>}
                  {sequence.name}
                </span>
                <span className="block text-sm text-gray-500 truncate">
                  {describeSteps(sequence, sceneName, t("SECONDS_SHORT"))}
                  {sequence.loop && ` · ${t("LOOP")}`}
                </span>
              </span>
              <span className="flex items-center gap-1 flex-shrink-0">
                <input type="checkbox" aria-label={t("ENABLED")} checked={sequence.enabled} onChange={() => toggle(sequence)} />
                <button onClick={() => setEditing(sequence)} aria-label={t("EDIT")} title={t("EDIT")} className="px-2">✎</button>
                <button onClick={() => remove(sequence)} aria-label={t("DELETE")} title={t("DELETE")} className="px-2 text-red-500">✕</button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <CNotice notice={notice} />
    </>
  );
}
