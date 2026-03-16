import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ApiProvider } from "./context/ApiContext";
import { AuthProvider } from "./context/AuthContext";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import ExpensesLayout from "./components/ExpensesLayout";
import DashboardLayout from "./components/DashboardLayout";
import BudgetLayout from "./components/BudgetLayout";
import WealthHubLayout from "./components/WealthHubLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Chat from "./pages/Chat";
import View from "./pages/View";
import Summary from "./pages/Summary";
import Dashboard from "./pages/Dashboard";
import Limits from "./pages/Limits";
import Review from "./pages/Review";
import Recurring from "./pages/Recurring";
import Insights from "./pages/Insights";
import Goals from "./pages/Goals";
import Affordability from "./pages/Affordability";
import Simulator from "./pages/Simulator";
import Settings from "./pages/Settings";
import FinanceNews from "./pages/FinanceNews";
import WealthSalary from "./pages/WealthSalary";
import WealthInvestments from "./pages/WealthInvestments";
import WealthPortfolio from "./pages/WealthPortfolio";
import WealthCashflow from "./pages/WealthCashflow";
import WealthProjections from "./pages/WealthProjections";
import WealthSuggestions from "./pages/WealthSuggestions";
import WealthManager from "./pages/WealthManager";
import WealthOverview from "./pages/WealthOverview";
import WealthGoals from "./pages/WealthGoals";
import WealthWatchlist from "./pages/WealthWatchlist";
import WealthNetWorth from "./pages/WealthNetWorth";

function App() {
  return (
    <ApiProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Chat />} />
            {/* Expenses: List, Summary, Review, Recurring */}
            <Route path="expenses" element={<ExpensesLayout />}>
              <Route index element={<Navigate to="/expenses/list" replace />} />
              <Route path="list" element={<View />} />
              <Route path="summary" element={<Summary />} />
              <Route path="review" element={<Review />} />
              <Route path="recurring" element={<Recurring />} />
            </Route>
            {/* Dashboard: Overview, Insights */}
            <Route path="dashboard" element={<DashboardLayout />}>
              <Route index element={<Navigate to="/dashboard/overview" replace />} />
              <Route path="overview" element={<Dashboard />} />
              <Route path="insights" element={<Insights />} />
            </Route>
            {/* Budget: Limits, Affordability, Simulator */}
            <Route path="budget" element={<BudgetLayout />}>
              <Route index element={<Navigate to="/budget/limits" replace />} />
              <Route path="limits" element={<Limits />} />
              <Route path="affordability" element={<Affordability />} />
              <Route path="simulator" element={<Simulator />} />
            </Route>
            {/* Wealth Hub: Overview, Income, Investments, Portfolio, Cashflow, Projections, Manager, Suggestions */}
            <Route path="wealth" element={<WealthHubLayout />}>
              <Route index element={<Navigate to="/wealth/overview" replace />} />
              <Route path="overview" element={<WealthOverview />} />
              <Route path="salary" element={<WealthSalary />} />
              <Route path="investments" element={<WealthInvestments />} />
              <Route path="portfolio" element={<WealthPortfolio />} />
              <Route path="manager" element={<WealthManager />} />
              <Route path="cashflow" element={<WealthCashflow />} />
              <Route path="projections" element={<WealthProjections />} />
              <Route path="suggestions" element={<WealthSuggestions />} />
              <Route path="goals" element={<WealthGoals />} />
              <Route path="watchlist" element={<WealthWatchlist />} />
              <Route path="net-worth" element={<WealthNetWorth />} />
            </Route>
            <Route path="goals" element={<Goals />} />
            <Route path="news" element={<FinanceNews />} />
            <Route path="settings" element={<Settings />} />
            {/* Redirect old URLs to new grouped URLs */}
            <Route path="view" element={<Navigate to="/expenses/list" replace />} />
            <Route path="summary" element={<Navigate to="/expenses/summary" replace />} />
            <Route path="review" element={<Navigate to="/expenses/review" replace />} />
            <Route path="recurring" element={<Navigate to="/expenses/recurring" replace />} />
            <Route path="limits" element={<Navigate to="/budget/limits" replace />} />
            <Route path="affordability" element={<Navigate to="/budget/affordability" replace />} />
            <Route path="simulator" element={<Navigate to="/budget/simulator" replace />} />
            <Route path="insights" element={<Navigate to="/dashboard/insights" replace />} />
            <Route path="finance-news" element={<Navigate to="/news" replace />} />
            <Route path="ask" element={<Navigate to="/" replace />} />
            <Route path="add" element={<Navigate to="/" replace />} />
            <Route path="gmail" element={<Navigate to="/settings" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </AuthProvider>
    </ApiProvider>
  );
}

export default App;
