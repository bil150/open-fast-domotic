import { FormEvent, useState } from "react";
import { useTranslation } from "react-i18next";
import { Scene, Sequence, SequenceInput, SequenceStep } from "../../api/types";

export interface CSequenceEditorProps {
  sequence: Sequence | null;
  scenes: Scene[];
  onSave: (sequence: SequenceInput) => void;
  onCancel: () => void;
}

const MAX_STEPS = 50;

/** Create/edit a sequence: scenes played one after the other, each held for a number of seconds. */
export function CSequenceEditor({ sequence, scenes, onSave, onCancel }: CSequenceEditorProps) {
  const { t } = useTranslation();
  const [name, setName] = useState(sequence?.name ?? "");
  const [steps, setSteps] = useState<SequenceStep[]>(
    sequence?.steps ?? [{ scene_id: scenes[0]?.id ?? 0, duration: 5, fade: true }]
  );
  const [loop, setLoop] = useState(sequence?.loop ?? true);
  const [enabled, setEnabled] = useState(sequence?.enabled ?? true);

  const patch = (index: number, change: Partial<SequenceStep>) =>
    setSteps((current) => current.map((s, i) => (i === index ? { ...s, ...change } : s)));
  const remove = (index: number) => setSteps((current) => current.filter((_, i) => i !== index));
  const add = () =>
    setSteps((current) => [...current, { scene_id: current[current.length - 1]?.scene_id ?? scenes[0]?.id ?? 0, duration: 5, fade: true }]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim() || steps.length === 0) return;
    onSave({ name: name.trim(), steps, loop, enabled });
  }

  const input = "bg-gray-200 dark:bg-gray-700 rounded p-2";

  return (
    <form onSubmit={submit} className="space-y-4 p-4 max-w-xl w-full mx-auto overflow-y-auto">
      <label className="block text-sm">
        {t("NAME")}
        <input required maxLength={60} value={name} onChange={(e) => setName(e.target.value)} className={`${input} w-full`} />
      </label>

      <ol className="space-y-2">
        {steps.map((step, index) => (
          <li key={index} className="flex items-center gap-2 border-2 border-gray-500 rounded-lg p-2">
            <span className="w-6 text-center text-gray-500">{index + 1}</span>
            <select
              aria-label={t("SCENE")}
              value={step.scene_id}
              onChange={(e) => patch(index, { scene_id: Number(e.target.value) })}
              className={`${input} flex-grow min-w-0`}
            >
              {scenes.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <input
              type="number"
              aria-label={t("DURATION")}
              min={1}
              max={86400}
              required
              value={step.duration}
              onChange={(e) => patch(index, { duration: Math.max(1, Math.round(Number(e.target.value)) || 1) })}
              className={`${input} w-20`}
            />
            <span className="text-sm">{t("SECONDS_SHORT")}</span>
            <label className="flex items-center gap-1 text-sm" title={t("FADE_STEP_HINT")}>
              <input type="checkbox" checked={step.fade ?? true} onChange={(e) => patch(index, { fade: e.target.checked })} />
              {t("FADE")}
            </label>
            <button
              type="button"
              onClick={() => remove(index)}
              disabled={steps.length === 1}
              aria-label={t("DELETE")}
              title={t("DELETE")}
              className="px-2 text-red-500 disabled:opacity-30"
            >
              ✕
            </button>
          </li>
        ))}
      </ol>
      <button
        type="button"
        onClick={add}
        disabled={steps.length >= MAX_STEPS}
        className="border-2 border-gray-400 rounded-full px-4 py-1 text-sm hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50"
      >
        + {t("ADD_STEP")}
      </button>

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} />
        {t("LOOP")}
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        {t("RUN_NOW")}
      </label>

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
