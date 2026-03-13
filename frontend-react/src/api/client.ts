const getBaseUrl = () => {
  const url = (typeof window !== "undefined" && (window as unknown as { __API_URL?: string }).__API_URL) ||
    import.meta.env.VITE_EXPENSE_API_URL ||
    "http://127.0.0.1:8000";
  return String(url).replace(/\/$/, "");
};

export function apiUrl(): string {
  return getBaseUrl();
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { params?: Record<string, string | number> } = {}
): Promise<T> {
  const { params, ...init } = options;
  let url = `${getBaseUrl()}${path}`;
  if (params && Object.keys(params).length > 0) {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => search.set(k, String(v)));
    url += `?${search.toString()}`;
  }
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return undefined as T;
}

// Expenses
export interface Expense {
  id?: number;
  date: string;
  category: string;
  amount: number;
  currency: string;
  raw_text?: string;
  is_verified?: number;
  confidence_score?: number;
}

export async function getExpenses(): Promise<Expense[]> {
  return apiFetch<Expense[]>("/expenses");
}

export async function addTextExpense(text: string): Promise<Expense> {
  return apiFetch<Expense>("/add-text-expense", { method: "POST", body: JSON.stringify({ text }) });
}

export async function addAudioExpense(file: Blob): Promise<Expense> {
  const base = getBaseUrl();
  const form = new FormData();
  form.append("file", file, "audio.wav");
  const res = await fetch(`${base}/add-audio-expense`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getReviewQueue(): Promise<Expense[]> {
  return apiFetch<Expense[]>("/expenses/review");
}

export async function verifyExpense(id: number, payload: { date?: string; category?: string; amount?: number; currency?: string }): Promise<Expense> {
  return apiFetch<Expense>(`/expenses/${id}/verify`, { method: "POST", body: JSON.stringify(payload) });
}

export async function deleteExpense(id: number): Promise<void> {
  await apiFetch(`/expenses/${id}`, { method: "DELETE" });
}

// Monthly summary
export async function getMonthlySummary(year: number, month: number): Promise<{ total_expenses: number; summary: string; expenses?: Expense[] }> {
  return apiFetch("/monthly-summary", { method: "POST", body: JSON.stringify({ year, month }) });
}

// Limits
export interface LimitStatus {
  year: number;
  month: number;
  limits: { category: string; amount: number; currency?: string }[];
  spending: Record<string, number>;
  alerts: { category: string; limit: number; spent: number; percent: number; alert_type: string }[];
}

export async function getLimitsStatus(year?: number, month?: number): Promise<LimitStatus> {
  const params: Record<string, number> = {};
  if (year != null) params.year = year;
  if (month != null) params.month = month;
  return apiFetch<LimitStatus>("/limits/status", { params });
}

export async function getLimits(): Promise<{ category: string; amount: number; currency?: string }[]> {
  return apiFetch("/limits");
}

export async function setLimit(category: string, amount: number, currency = "USD"): Promise<void> {
  await apiFetch("/limits", { method: "POST", body: JSON.stringify({ category, amount, currency }) });
}

export async function deleteLimit(category: string): Promise<void> {
  await apiFetch(`/limits/${category}`, { method: "DELETE" });
}

// Forecast & alerts
export async function getForecastMonth(year?: number, month?: number): Promise<{ projected_total: number; by_category?: Record<string, number>; days_elapsed?: number; days_in_month?: number }> {
  return apiFetch("/forecast/month", { params: year != null && month != null ? { year, month } : {} });
}

export async function getForecastCategories(year?: number, month?: number): Promise<Record<string, number> | unknown[]> {
  return apiFetch("/forecast/categories", { params: year != null && month != null ? { year, month } : {} });
}

export async function getPredictiveAlerts(year?: number, month?: number): Promise<{ alerts: { message: string }[] }> {
  return apiFetch("/alerts/predictive", { params: year != null && month != null ? { year, month } : {} });
}

// Insights
export async function getInsightsOverview(params: { start_date?: string; end_date?: string }): Promise<Record<string, unknown>> {
  return apiFetch("/insights/overview", { params: params as Record<string, string> });
}

export async function getInsightsCategories(params: { start_date?: string; end_date?: string }): Promise<unknown> {
  return apiFetch("/insights/categories", { params: params as Record<string, string> });
}

export async function getInsightsHealthScore(): Promise<{ score: number; metrics?: Record<string, unknown> }> {
  return apiFetch("/insights/health-score");
}

export async function getInsightsTrends(months?: number): Promise<{ trends?: { label: string; total_spend: number; transaction_count: number }[] }> {
  return apiFetch("/insights/trends", { params: months != null ? { months } : {} });
}

export async function getInsightsRecommendations(): Promise<{ recommendations?: { title: string; suggestion: string; metric_cited?: string; value?: unknown }[] }> {
  return apiFetch("/insights/recommendations");
}

export async function getInsightsAnomalies(params: { start_date?: string; end_date?: string }): Promise<{ anomalies?: unknown[] }> {
  return apiFetch("/insights/anomalies", { params: params as Record<string, string> });
}

export async function getInsightsNarrative(params: { start_date?: string; end_date?: string }): Promise<{ narrative?: string }> {
  return apiFetch("/insights/narrative", { params: params as Record<string, string> });
}

export async function getRecurring(): Promise<{ items?: unknown[] }> {
  return apiFetch("/insights/recurring");
}

export async function recomputeRecurring(): Promise<unknown> {
  return apiFetch("/insights/recurring/recompute", { method: "POST" });
}

// Ask
export async function ask(question: string): Promise<{ answer: string; filters_used?: unknown; supporting_data?: unknown }> {
  return apiFetch("/ask", { method: "POST", body: JSON.stringify({ question }) });
}

// Goals
export interface Goal {
  id: number;
  goal_type: string;
  target_amount: number;
  current_amount: number;
  target_date?: string;
  category?: string;
  description?: string;
  status?: string;
  distance?: Record<string, unknown>;
  suggested_reduction_per_month?: number;
  suggested_reduction_per_week?: number;
}

export async function getGoals(status = "active"): Promise<Goal[]> {
  return apiFetch<Goal[]>("/goals", { params: { status } });
}

export async function createGoal(payload: {
  goal_type: string;
  target_amount: number;
  current_amount: number;
  target_date?: string | null;
  category?: string | null;
  description?: string | null;
}): Promise<Goal> {
  return apiFetch<Goal>("/goals", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateGoal(id: number, payload: Partial<Goal>): Promise<Goal> {
  return apiFetch<Goal>(`/goals/${id}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteGoal(id: number): Promise<void> {
  await apiFetch(`/goals/${id}`, { method: "DELETE" });
}

// Affordability
export async function checkAffordability(payload: { amount: number; category?: string | null; merchant?: string | null }): Promise<{
  can_afford: boolean;
  recommendation_text: string;
  reasons: string[];
  projected_impact?: unknown;
  budget_impact?: unknown;
  goal_impact?: unknown;
}> {
  return apiFetch("/affordability/check", { method: "POST", body: JSON.stringify(payload) });
}

// Simulate
export interface SimulateAdjustment {
  type: string;
  category?: string;
  value?: number;
  amount?: number;
  merchant?: string;
}

export async function simulate(adjustments: SimulateAdjustment[]): Promise<{
  baseline_summary?: { projected_total?: number; by_category?: Record<string, number> };
  simulated_summary?: { projected_total?: number; by_category?: Record<string, number> };
  delta_summary?: { total_change?: number };
  projected_limit_changes?: unknown[];
  goal_impact?: unknown[];
}> {
  return apiFetch("/simulate", { method: "POST", body: JSON.stringify({ adjustments }) });
}

// Gmail
export async function getGmailStatus(): Promise<{ connected?: boolean; message?: string }> {
  return apiFetch("/gmail/status");
}

export async function syncGmail(): Promise<{ synced?: number; message?: string }> {
  return apiFetch("/gmail/sync", { method: "POST", body: JSON.stringify({}) });
}

// Health
export async function apiHealth(): Promise<{ status?: string }> {
  return apiFetch("/");
}
