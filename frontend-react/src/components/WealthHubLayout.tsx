import { Outlet } from "react-router-dom";
import WealthHubSectionNav from "./WealthHubSectionNav";
import WealthHubSummaryBar from "./WealthHubSummaryBar";
import { WEALTH_ROUTES } from "../wealth";

const navGroups = [
  {
    label: "Money In",
    items: [
      { to: WEALTH_ROUTES.overview, label: "Overview" },
      { to: WEALTH_ROUTES.salary, label: "Income" },
      { to: WEALTH_ROUTES.cashflow, label: "Cashflow" },
    ],
  },
  {
    label: "Wealth Build",
    items: [
      { to: WEALTH_ROUTES.investments, label: "Investments" },
      { to: WEALTH_ROUTES.portfolio, label: "Portfolio" },
      { to: WEALTH_ROUTES.manager, label: "Portfolio Intelligence" },
    ],
  },
  {
    label: "Guidance",
    items: [
      { to: WEALTH_ROUTES.projections, label: "Projections" },
      { to: WEALTH_ROUTES.suggestions, label: "Suggestions" },
    ],
  },
  {
    label: "Planning",
    items: [
      { to: WEALTH_ROUTES.goals, label: "Goals" },
      { to: WEALTH_ROUTES.watchlist, label: "Watchlist" },
      { to: WEALTH_ROUTES.netWorth, label: "Net Worth" },
    ],
  },
];

export default function WealthHubLayout() {
  return (
    <>
      <WealthHubSectionNav groups={navGroups} title="Wealth Hub" />
      <WealthHubSummaryBar />
      <Outlet />
    </>
  );
}
