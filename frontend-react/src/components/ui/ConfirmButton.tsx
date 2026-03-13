import { useState } from "react";

export default function ConfirmButton({
  label,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  onConfirm,
  variant = "danger",
  className = "",
}: {
  label: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void | Promise<void>;
  variant?: "danger" | "secondary";
  className?: string;
}) {
  const [confirming, setConfirming] = useState(false);

  const handleClick = () => {
    if (confirming) {
      Promise.resolve(onConfirm()).then(() => setConfirming(false));
    } else {
      setConfirming(true);
    }
  };

  const base = "text-sm font-medium rounded-lg px-3 py-1.5 transition-colors " + className;
  const danger = "text-red-400 hover:bg-red-500/10";
  const secondary = "text-text-secondary hover:bg-surface-muted";

  if (confirming) {
    return (
      <span className="inline-flex items-center gap-2">
        <button
          type="button"
          className={base + " " + (variant === "danger" ? danger : secondary)}
          onClick={handleClick}
        >
          {confirmLabel}
        </button>
        <button
          type="button"
          className={base + " text-text-secondary hover:bg-surface-muted"}
          onClick={() => setConfirming(false)}
        >
          {cancelLabel}
        </button>
      </span>
    );
  }

  return (
    <button
      type="button"
      className={base + " " + (variant === "danger" ? "text-red-400 hover:bg-red-500/10" : secondary)}
      onClick={handleClick}
    >
      {label}
    </button>
  );
}
