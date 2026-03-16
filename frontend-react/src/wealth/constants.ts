/**
 * Shared Wealth Hub constants and helpers.
 * Use for route paths, section styling, and current period.
 */

export const WEALTH_ROUTES = {
  overview: "/wealth/overview",
  salary: "/wealth/salary",
  investments: "/wealth/investments",
  portfolio: "/wealth/portfolio",
  cashflow: "/wealth/cashflow",
  projections: "/wealth/projections",
  manager: "/wealth/manager",
  suggestions: "/wealth/suggestions",
  goals: "/wealth/goals",
  watchlist: "/wealth/watchlist",
  netWorth: "/wealth/net-worth",
} as const;

const now = new Date();
export const currentYear = now.getFullYear();
export const currentMonth = now.getMonth() + 1;

/** Tailwind class for Wealth Hub section headings (h2). */
export const SECTION_HEADING_CLASS = "text-lg font-semibold text-text-primary mb-4";

/** Tailwind class for Wealth Hub card section headings (h2/h3). */
export const CARD_HEADING_CLASS = "text-lg font-semibold text-text-primary mb-3";

export const MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] as const;
