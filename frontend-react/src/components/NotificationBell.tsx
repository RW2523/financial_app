import { useState, useRef, useEffect } from "react";
import { clsx } from "clsx";
import { Bell, AlertTriangle, AlertCircle } from "lucide-react";

export interface LimitAlert {
  category: string;
  limit: number;
  spent: number;
  percent: number;
  alert_type: string;
}

export default function NotificationBell({ alerts }: { alerts: LimitAlert[] }) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [open]);

  const count = alerts?.length ?? 0;

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={clsx(
          "relative p-2 rounded-lg transition-colors",
          "text-text-secondary hover:text-text-primary hover:bg-surface-muted",
          "focus:outline-none focus:ring-2 focus:ring-accent/50"
        )}
        aria-label={count > 0 ? `${count} alerts` : "Notifications"}
        aria-expanded={open}
      >
        <Bell className="h-5 w-5" />
        {count > 0 && (
          <span
            className={clsx(
              "absolute -top-0.5 -right-0.5 flex items-center justify-center min-w-[18px] h-[18px] rounded-full text-xs font-semibold",
              "bg-red-500 text-white"
            )}
          >
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-80 max-w-[calc(100vw-2rem)] bg-surface-elevated border border-border rounded-lg shadow-lg z-50 py-2"
          role="menu"
        >
          <div className="px-4 pb-2 border-b border-border">
            <h3 className="font-medium text-text-primary text-sm">Notifications</h3>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {count === 0 ? (
              <p className="px-4 py-4 text-sm text-text-muted">No alerts right now.</p>
            ) : (
              <ul className="py-1">
                {alerts.map((a, i) => (
                  <li
                    key={i}
                    className={clsx(
                      "flex items-center gap-2 px-4 py-2.5 text-sm",
                      a.alert_type === "over" ? "text-red-400" : "text-amber-400"
                    )}
                  >
                    {a.alert_type === "over" ? (
                      <AlertCircle className="h-4 w-4 shrink-0" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                    )}
                    <span>
                      {a.alert_type === "over" ? "Over" : "Near"} limit: {a.category} — $
                      {a.spent.toFixed(2)} / ${a.limit.toFixed(2)} ({a.percent}%)
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
