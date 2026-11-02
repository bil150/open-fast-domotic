import { Notice } from "../../../hooks/useNotice";

export function CNotice({ notice }: { notice: Notice | null }) {
  if (!notice) return null;
  const color = notice.kind === "error" ? "bg-red-600" : "bg-green-600";
  return (
    <div
      role="status"
      className={`fixed bottom-16 left-1/2 -translate-x-1/2 z-20 max-w-[90%] px-4 py-2 rounded-2xl text-white text-sm shadow-lg ${color}`}
    >
      {notice.text}
    </div>
  );
}
