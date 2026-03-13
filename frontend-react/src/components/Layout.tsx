import { useState, useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { clsx } from "clsx";
import {
  PlusCircle,
  List,
  BarChart3,
  LayoutDashboard,
  Bell,
  Mail,
  CheckSquare,
  RefreshCw,
  Lightbulb,
  MessageCircle,
  Target,
  CreditCard,
  Sparkles,
  Settings,
  Wallet,
} from "lucide-react";
import { getLimitsStatus } from "../api/client";
import AlertBanner from "./AlertBanner";

const nav = [
  { to: "/", label: "Add", icon: PlusCircle },
  { to: "/view", label: "View", icon: List },
  { to: "/summary", label: "Summary", icon: BarChart3 },
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/limits", label: "Limits", icon: Bell },
  { to: "/gmail", label: "Gmail", icon: Mail },
  { to: "/review", label: "Review Queue", icon: CheckSquare },
  { to: "/recurring", label: "Recurring", icon: RefreshCw },
  { to: "/insights", label: "Insights", icon: Lightbulb },
  { to: "/ask", label: "Ask AI", icon: MessageCircle },
  { to: "/goals", label: "Goals", icon: Target },
  { to: "/affordability", label: "Affordability", icon: CreditCard },
  { to: "/simulator", label: "Simulator", icon: Sparkles },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
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
            <Wallet className="h-8 w-8 text-accent" />
            <span className="font-semibold text-text-primary">Expense Tracker</span>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
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
        <AlertBanner alerts={alerts} />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
