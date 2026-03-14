import { useState, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { clsx } from "clsx";
import {
  MessageCircle,
  List,
  LayoutDashboard,
  PiggyBank,
  Target,
  Newspaper,
  Settings,
} from "lucide-react";
import { getLimitsStatus } from "../api/client";
import { useAuth } from "../context/AuthContext";
import NotificationBell from "./NotificationBell";

const nav = [
  { to: "/", label: "Chat", icon: MessageCircle, end: true },
  { to: "/expenses", label: "Expenses", icon: List, end: false },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: false },
  { to: "/budget", label: "Budget", icon: PiggyBank, end: false },
  { to: "/goals", label: "Goals", icon: Target, end: true },
  { to: "/news", label: "News", icon: Newspaper, end: true },
  { to: "/settings", label: "Settings", icon: Settings, end: true },
];

export default function Layout() {
  const { user } = useAuth();
  const [alerts, setAlerts] = useState<{ category: string; limit: number; spent: number; percent: number; alert_type: string }[]>([]);

  useEffect(() => {
    getLimitsStatus()
      .then((s) => setAlerts(s.alerts ?? []))
      .catch(() => setAlerts([]));
  }, []);

  return (
    <div className="flex min-h-screen bg-surface">
      <aside className="w-56 shrink-0 border-r border-border bg-surface-elevated flex flex-col">
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <img src="/icon.png" alt="" className="h-8 w-8 rounded-lg shrink-0" />
            <span className="font-semibold text-text-primary">SelavAI</span>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-accent-muted text-accent border border-accent/30"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-muted"
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="flex items-center justify-end gap-3 shrink-0 h-12 px-4 border-b border-border bg-surface-elevated">
          {user && (
            <span className="text-sm text-text-secondary" title={`Salary: ${user.currency} ${user.salary}; Budget: ${user.currency} ${user.monthly_budget}`}>
              {user.username}
            </span>
          )}
          <NotificationBell alerts={alerts} />
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
