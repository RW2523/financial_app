import { Outlet } from "react-router-dom";
import SectionNav from "./SectionNav";

const tabs = [
  { to: "/budget/limits", label: "Limits" },
  { to: "/budget/affordability", label: "Affordability" },
  { to: "/budget/simulator", label: "Simulator" },
];

export default function BudgetLayout() {
  return (
    <>
      <SectionNav items={tabs} title="Budget" />
      <Outlet />
    </>
  );
}
