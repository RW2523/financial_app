/** Format number as USD (or pass currency for display). */
export function formatMoney(amount: number, currency = "USD"): string {
  return `${currency} ${Number(amount).toFixed(2)}`;
}

/** Format date string for display (YYYY-MM-DD → same or truncated). */
export function formatDate(dateStr: string | undefined): string {
  return dateStr?.slice(0, 10) ?? "—";
}
