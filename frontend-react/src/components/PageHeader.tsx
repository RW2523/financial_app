import type { ReactNode } from "react";

export default function PageHeader({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return (
    <div className="border-b border-border bg-surface-elevated px-6 py-5">
      <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-text-secondary">{subtitle}</p>}
      {children}
    </div>
  );
}
