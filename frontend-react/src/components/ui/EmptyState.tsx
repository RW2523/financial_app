import type { ReactNode } from "react";

export default function EmptyState({ message, children }: { message: string; children?: ReactNode }) {
  return (
    <div className="card text-center py-12 text-text-secondary">
      <p className="mb-4">{message}</p>
      {children}
    </div>
  );
}
