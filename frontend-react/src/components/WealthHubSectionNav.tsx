import { NavLink } from "react-router-dom";
import { clsx } from "clsx";
import { WEALTH_ROUTES } from "../wealth";

export interface SectionItem {
  to: string;
  label: string;
}

export interface NavGroup {
  label: string;
  items: SectionItem[];
}

export default function WealthHubSectionNav({ groups, title }: { groups: NavGroup[]; title?: string }) {
  return (
    <div className="border-b border-border bg-surface-elevated/50 px-4">
      {title && (
        <h2 className="text-sm font-medium text-text-secondary pt-3 pb-1">{title}</h2>
      )}
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2 -mb-px">
        {groups.map((group) => (
          <div key={group.label} className="flex items-center gap-2">
            <span className="text-xs font-medium text-text-muted uppercase tracking-wide shrink-0">
              {group.label}
            </span>
            <nav className="flex gap-1" aria-label={group.label}>
              {group.items.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === WEALTH_ROUTES.overview}
                  className={({ isActive }) =>
                    clsx(
                      "px-3 py-2.5 text-sm font-medium border-b-2 transition-colors",
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
        ))}
      </div>
    </div>
  );
}
