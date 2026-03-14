import { NavLink } from "react-router-dom";
import { clsx } from "clsx";

export interface SectionItem {
  to: string;
  label: string;
}

export default function SectionNav({ items, title }: { items: SectionItem[]; title?: string }) {
  return (
    <div className="border-b border-border bg-surface-elevated/50 px-4">
      {title && (
        <h2 className="text-sm font-medium text-text-secondary pt-3 pb-1">{title}</h2>
      )}
      <nav className="flex gap-1 -mb-px" aria-label="Section">
        {items.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={false}
            className={({ isActive }) =>
              clsx(
                "px-4 py-3 text-sm font-medium border-b-2 transition-colors",
                isActive
                  ? "border-accent text-accent"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              )
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
