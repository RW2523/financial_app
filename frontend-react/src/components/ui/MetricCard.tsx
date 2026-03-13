import type { ReactNode } from "react";

export default function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="card">
      <p className="text-text-secondary text-sm">{label}</p>
      <p className={`text-xl font-semibold mt-1 ${accent ? "text-accent" : "text-text-primary"}`}>{value}</p>
      {sub != null && sub !== "" && <p className="text-text-muted text-xs mt-0.5">{sub}</p>}
    </div>
  );
}
