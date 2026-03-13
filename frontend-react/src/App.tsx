import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ApiProvider } from "./context/ApiContext";
import Layout from "./components/Layout";
import Add from "./pages/Add";
import View from "./pages/View";
import Summary from "./pages/Summary";
import Dashboard from "./pages/Dashboard";
import Limits from "./pages/Limits";
import Gmail from "./pages/Gmail";
import Review from "./pages/Review";
import Recurring from "./pages/Recurring";
import Insights from "./pages/Insights";
import Ask from "./pages/Ask";
import Goals from "./pages/Goals";
import Affordability from "./pages/Affordability";
import Simulator from "./pages/Simulator";
import Settings from "./pages/Settings";

function App() {
  return (
    <ApiProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Add />} />
            <Route path="view" element={<View />} />
            <Route path="summary" element={<Summary />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="limits" element={<Limits />} />
            <Route path="gmail" element={<Gmail />} />
            <Route path="review" element={<Review />} />
            <Route path="recurring" element={<Recurring />} />
            <Route path="insights" element={<Insights />} />
            <Route path="ask" element={<Ask />} />
            <Route path="goals" element={<Goals />} />
            <Route path="affordability" element={<Affordability />} />
            <Route path="simulator" element={<Simulator />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ApiProvider>
  );
}

export default App;
