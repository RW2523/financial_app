const getBaseUrl = () => {
  const url = (typeof window !== "undefined" && (window as unknown as { __API_URL?: string }).__API_URL) ||
    import.meta.env.VITE_EXPENSE_API_URL ||
    "http://127.0.0.1:8000";
  return String(url).replace(/\/$/, "");
};

let _apiUserId: string | null = null;

export function setApiUserId(userId: string | null) {
  _apiUserId = userId;
}

/** Headers to add to API requests (e.g. X-User-Id). Use for fetch() calls that don't go through apiFetch. */
export function getApiHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
  if (_apiUserId) h["X-User-Id"] = _apiUserId;
  return h;
}

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
  const headers: Record<string, string> = { "Content-Type": "application/json", ...(init.headers as Record<string, string>) };
  if (_apiUserId) headers["X-User-Id"] = _apiUserId;
  const res = await fetch(url, {
    ...init,
    headers,
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
  const res = await fetch(`${base}/add-audio-expense`, { method: "POST", body: form, headers: getApiHeaders() });
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

// Chat (unified add + ask)
export type ChatResponse =
  | { type: "expense_added"; expense: { id?: number; date: string; category: string; amount: number; currency: string; raw_text?: string }; message: string }
  | { type: "answer"; answer_text: string; question: string; refused?: boolean; rows?: unknown[]; aggregates?: unknown };

export async function chat(
  message: string,
  history?: { role: string; content: string }[]
): Promise<ChatResponse> {
  return apiFetch("/chat", {
    method: "POST",
    body: JSON.stringify({ message, history: history ?? [] }),
  });
}

export async function chatVoice(file: Blob): Promise<ChatResponse & { transcript?: string }> {
  const base = getBaseUrl();
  const form = new FormData();
  form.append("file", file, "audio.wav");
  const res = await fetch(`${base}/chat-voice`, { method: "POST", body: form, headers: getApiHeaders() });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface DocumentExpensesResponse {
  added: number;
  expenses: Expense[];
  message: string;
  ocr_available?: boolean;
  pdf_available?: boolean;
}

export async function addDocumentExpenses(
  files: File[],
  message?: string
): Promise<DocumentExpensesResponse> {
  const base = getBaseUrl();
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  if (message != null && message.trim()) form.append("message", message.trim());
  const res = await fetch(`${base}/add-document-expenses`, {
    method: "POST",
    body: form,
    headers: getApiHeaders(),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
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
export async function getGmailStatus(): Promise<{
  connected?: boolean;
  configured?: boolean;
  message?: string;
  credentials_path?: string;
  token_path?: string;
  error?: string;
}> {
  return apiFetch("/gmail/status");
}

export async function syncGmail(body?: { query?: string; max_results?: number }): Promise<{ added?: number; errors?: string[] }> {
  return apiFetch("/gmail/sync", { method: "POST", body: JSON.stringify(body ?? {}) });
}

// Clear all data (Settings)
export async function clearAllData(): Promise<{ ok: boolean; deleted: { expenses: number; limits: number; goals: number; recurring: number; gmail_processed: number } }> {
  return apiFetch("/admin/clear-data", { method: "POST", body: JSON.stringify({ confirm: true }) });
}

export async function addSampleData(): Promise<{ ok: boolean; expenses: number; limits: number; goals: number }> {
  return apiFetch("/admin/seed-sample-data", { method: "POST" });
}

// Finance news (Tavily)
export interface FinanceNewsItem {
  title: string;
  url: string;
  content: string;
  score?: number;
}

export async function getFinanceNews(params?: { query?: string; max_results?: number; time_range?: string }): Promise<{
  results: FinanceNewsItem[];
  query?: string;
  response_time?: number;
  error?: string;
}> {
  const search = new URLSearchParams();
  if (params?.query) search.set("query", params.query);
  if (params?.max_results != null) search.set("max_results", String(params.max_results));
  if (params?.time_range) search.set("time_range", params.time_range);
  const qs = search.toString();
  return apiFetch(`/news/finance${qs ? `?${qs}` : ""}`);
}

// Auth
export interface AuthUser {
  user_id: string;
  username: string;
  salary: number;
  monthly_budget: number;
  currency: string;
  display_name?: string;
}

export async function authLogin(username: string, password: string): Promise<AuthUser> {
  return apiFetch("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
}

export async function authRegister(params: {
  username: string;
  password: string;
  salary?: number;
  monthly_budget?: number;
  currency?: string;
}): Promise<AuthUser> {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      username: params.username,
      password: params.password,
      salary: params.salary ?? 0,
      monthly_budget: params.monthly_budget ?? 0,
      currency: params.currency ?? "USD",
    }),
  });
}

// Health
export async function apiHealth(): Promise<{ status?: string }> {
  return apiFetch("/");
}
