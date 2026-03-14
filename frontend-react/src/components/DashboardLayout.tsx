import { Outlet } from "react-router-dom";
import SectionNav from "./SectionNav";

const tabs = [
  { to: "/dashboard/overview", label: "Overview" },
  { to: "/dashboard/insights", label: "Insights" },
];

export default function DashboardLayout() {
  return (
    <>
      <SectionNav items={tabs} title="Dashboard" />
      <Outlet />
    </>
  );
}
