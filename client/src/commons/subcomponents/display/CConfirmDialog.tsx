import { useEffect } from "react";
import { useTranslation } from "react-i18next";

export interface CConfirmDialogProps {
  title: string;
  message?: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** A confirmation inside the page (not the browser's). Escape or a click outside cancels. */
export function CConfirmDialog(props: CConfirmDialogProps) {
  const { t } = useTranslation();
  const { onCancel } = props;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div
      className="fixed inset-0 z-30 flex items-center justify-center bg-black/50 px-4"
      onClick={props.onCancel}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={props.title}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-2xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-5 shadow-xl"
      >
        <h3 className="text-lg">{props.title}</h3>
        {props.message && <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{props.message}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button
            autoFocus
            type="button"
            onClick={props.onCancel}
            className="px-4 py-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            {t("CANCEL")}
          </button>
          <button
            type="button"
            onClick={props.onConfirm}
            className="border-2 border-gray-400 rounded-full px-5 py-2 text-red-500 hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            {props.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
