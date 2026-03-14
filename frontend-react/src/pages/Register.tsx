import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authRegister } from "../api/client";
import { ErrorMessage } from "../components/ui";

export default function Register() {
  const navigate = useNavigate();
  const { user, login } = useAuth();
  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [salary, setSalary] = useState("");
  const [monthlyBudget, setMonthlyBudget] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await authRegister({
        username: username.trim(),
        password,
        salary: parseFloat(salary) || 0,
        monthly_budget: parseFloat(monthlyBudget) || 0,
        currency,
      });
      login(user);
      navigate("/", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface p-4">
      <div className="w-full max-w-sm card">
        <div className="flex flex-col items-center gap-2 mb-6">
          <img src="/icon.png" alt="" className="h-12 w-12 rounded-xl" />
          <span className="text-xl font-semibold text-text-primary">SelavAI</span>
          <span className="text-sm text-text-secondary">Personal Financial Assistant</span>
        </div>
        <h1 className="text-lg font-medium text-text-primary mb-2 text-center">Sign up</h1>
        <p className="text-sm text-text-secondary mb-4 text-center">Create an account and set your budget basics.</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm text-text-secondary">Username</span>
            <input
              type="text"
              className="input-field mt-1 w-full"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              minLength={2}
            />
          </label>
          <label className="block">
            <span className="text-sm text-text-secondary">Password</span>
            <input
              type="password"
              className="input-field mt-1 w-full"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
              minLength={4}
            />
          </label>
          <label className="block">
            <span className="text-sm text-text-secondary">Monthly salary (optional)</span>
            <input
              type="number"
              step="0.01"
              min="0"
              className="input-field mt-1 w-full"
              value={salary}
              onChange={(e) => setSalary(e.target.value)}
              placeholder="e.g. 5000"
            />
          </label>
          <label className="block">
            <span className="text-sm text-text-secondary">Monthly budget (optional)</span>
            <input
              type="number"
              step="0.01"
              min="0"
              className="input-field mt-1 w-full"
              value={monthlyBudget}
              onChange={(e) => setMonthlyBudget(e.target.value)}
              placeholder="e.g. 3500"
            />
          </label>
          <label className="block">
            <span className="text-sm text-text-secondary">Currency</span>
            <select
              className="input-field mt-1 w-full"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
              <option value="INR">INR</option>
            </select>
          </label>
          {error && <ErrorMessage message={error} />}
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Creating account…" : "Sign up"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-text-secondary">
          Already have an account? <Link to="/login" className="text-accent hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
