import { clsx } from "clsx";
import { AlertTriangle, AlertCircle } from "lucide-react";

interface Alert {
  category: string;
  limit: number;
  spent: number;
  percent: number;
  alert_type: string;
}

export default function AlertBanner({ alerts }: { alerts: Alert[] }) {
  if (!alerts?.length) return null;
  return (
    <div className="bg-surface-elevated border-b border-border px-6 py-3 space-y-2">
      {alerts.map((a, i) => (
        <div
          key={i}
          className={clsx(
            "flex items-center gap-2 text-sm font-medium",
            a.alert_type === "over" ? "text-red-400" : "text-amber-400"
          )}
        >
          {a.alert_type === "over" ? (
            <AlertCircle className="h-4 w-4 shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 shrink-0" />
          )}
          <span>
            {a.alert_type === "over" ? "Over" : "Near"} limit: {a.category} — ${a.spent.toFixed(2)} / ${a.limit.toFixed(2)} ({a.percent}%)
          </span>
        </div>
      ))}
    </div>
  );
}
