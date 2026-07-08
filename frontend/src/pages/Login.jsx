import { useEffect, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";
import { googleAuthorizeUrl } from "../api.js";
import { Icon } from "../components/icons.jsx";

export default function Login() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get("error")) {
      setError("Sign-in didn't go through. Try again.");
    }
  }, [location.search]);

  if (!loading && isAuthenticated) {
    return <Navigate to="/app" replace />;
  }

  const signIn = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(googleAuthorizeUrl());
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Google sign-in is not configured");
      window.location.href = data.authorization_url;
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-ink-900 px-6 text-fg">
      <div className="w-full max-w-sm">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand text-ink-900">
            <Icon.Brain width={19} height={19} />
          </span>
          <span className="font-display text-lg font-semibold">Profiler</span>
        </Link>

        <div className="card-natural p-7 text-center">
          <h1 className="font-display text-2xl font-semibold">Welcome back</h1>
          <p className="mt-2 text-sm text-fg-muted">
            Sign in to see your procrastination model. Your data stays scoped to your account.
          </p>

          <button
            onClick={signIn}
            disabled={busy}
            className="btn-primary mt-7 w-full justify-center py-3 text-sm disabled:opacity-60"
          >
            <GoogleG />
            {busy ? "Redirecting…" : "Sign in with Google"}
          </button>

          {error && <p className="mt-4 text-xs text-bad">{error}</p>}

          <p className="mt-6 text-xs leading-relaxed text-fg-faint">
            Local-first. Your tasks, events, and check-ins are stored only under your account.
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleG() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24">
      <path
        fill="currentColor"
        d="M21.35 11.1h-9.17v2.73h6.51c-.33 3.81-3.5 5.44-6.5 5.44C8.36 19.27 5 16.25 5 12c0-4.1 3.2-7.27 7.2-7.27 3.09 0 4.9 1.97 4.9 1.97L19 4.72S16.56 2 12.1 2C6.42 2 2.03 6.8 2.03 12c0 5.05 4.13 10 10.22 10 5.35 0 9.25-3.67 9.25-9.09 0-1.15-.15-1.81-.15-1.81Z"
      />
    </svg>
  );
}
