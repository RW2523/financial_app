/**
 * Format a signed money delta for display (e.g. month-over-month change).
 */
import { formatMoney } from "../lib/utils";

export function formatDelta(value: number | null | undefined): string {
  if (value == null) return "—";
  const prefix = value >= 0 ? "+" : "";
  return prefix + formatMoney(value);
}
