import { Link } from "react-router-dom";
import { WEALTH_ROUTES } from "./constants";
import type { Suggestion } from "../api/client";

export interface MiniSuggestionsBlockProps {
  title: string;
  suggestions: Suggestion[];
  viewAllLabel?: string;
  /** When true, show only suggestion title (and link); no message body. */
  compact?: boolean;
}

/**
 * Renders a short list of suggestions with optional destination links and a "View all" link.
 */
export default function MiniSuggestionsBlock({
  title,
  suggestions,
  viewAllLabel = "View all suggestions",
  compact = false,
}: MiniSuggestionsBlockProps) {
  if (suggestions.length === 0) return null;

  return (
    <section className="card">
      <h2 className="text-lg font-semibold text-text-primary mb-2">{title}</h2>
      <ul className="space-y-2">
        {suggestions.map((s) => (
          <li key={s.id}>
            {s.destination ? (
              <Link
                to={s.destination}
                className={compact ? "text-accent hover:underline text-sm" : "block p-2 rounded bg-surface-muted hover:bg-surface-elevated text-sm"}
              >
                <span className="font-medium text-text-primary">{s.title}</span>
                {!compact && <p className="text-text-secondary mt-0.5">{s.message}</p>}
              </Link>
            ) : (
              compact ? (
                <span className="text-sm text-text-secondary">{s.title}</span>
              ) : (
                <div className="p-2 rounded bg-surface-muted text-sm">
                  <span className="font-medium text-text-primary">{s.title}</span>
                  <p className="text-text-secondary mt-0.5">{s.message}</p>
                </div>
              )
            )}
          </li>
        ))}
      </ul>
      <Link
        to={WEALTH_ROUTES.suggestions}
        className="text-accent hover:underline text-sm mt-2 inline-block"
      >
        {viewAllLabel}
      </Link>
    </section>
  );
}
