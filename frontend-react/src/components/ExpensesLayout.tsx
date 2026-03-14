import { Outlet } from "react-router-dom";
import SectionNav from "./SectionNav";

const tabs = [
  { to: "/expenses/list", label: "List" },
  { to: "/expenses/summary", label: "Summary" },
  { to: "/expenses/review", label: "Review" },
  { to: "/expenses/recurring", label: "Recurring" },
];

export default function ExpensesLayout() {
  return (
    <>
      <SectionNav items={tabs} title="Expenses" />
      <Outlet />
    </>
  );
}
