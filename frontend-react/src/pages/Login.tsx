import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { authLogin, apiUrl } from "../api/client";
import { ErrorMessage } from "../components/ui";

export default function Login() {
  const navigate = useNavigate();
  const { user, login } = useAuth();
  useEffect(() => {
    if (user) navigate("/", { replace: true });
  }, [user, navigate]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await authLogin(username.trim(), password);
      login(user);
      navigate("/", { replace: true });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Login failed.";
      const is404 = typeof msg === "string" && (msg.includes("Not Found") || msg.includes('"detail"'));
      setError(is404
        ? `Backend returned Not Found. Ensure the API is running and restarted (e.g. ./run_all.sh). API URL: ${apiUrl()}`
        : msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDefaultLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      const user = await authLogin("demo", "demo");
      login(user);
      navigate("/", { replace: true });
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Default login failed.";
      const is404 = typeof msg === "string" && (msg.includes("Not Found") || msg.includes('"detail"'));
      setError(is404
        ? `Backend returned Not Found. Ensure the API is running and restarted (e.g. ./run_all.sh). API URL: ${apiUrl()}`
        : msg);
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
        <h1 className="text-lg font-medium text-text-primary mb-4 text-center">Sign in</h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <label className="block">
            <span className="text-sm text-text-secondary">Username</span>
            <input
              type="text"
              className="input-field mt-1 w-full"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="block">
            <span className="text-sm text-text-secondary">Password</span>
            <input
              type="password"
              className="input-field mt-1 w-full"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <ErrorMessage message={error} />}
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="mt-6 pt-4 border-t border-border">
          <p className="text-sm text-text-secondary mb-2">Try the app with sample data:</p>
          <button
            type="button"
            className="btn-secondary w-full border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
            onClick={handleDefaultLogin}
            disabled={loading}
          >
            Default login (demo account)
          </button>
        </div>
        <p className="mt-4 text-center text-sm text-text-secondary">
          No account? <Link to="/register" className="text-accent hover:underline">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
