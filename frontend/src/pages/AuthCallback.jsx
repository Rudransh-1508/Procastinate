// Landing spot for the Google OAuth redirect: /auth/callback?token=...
import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../AuthContext.jsx";
import { Spinner } from "../components/ui.jsx";

export default function AuthCallback() {
  const [params] = useSearchParams();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setError("Missing token in callback URL.");
      return;
    }
    login(token);
    navigate("/app", { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  if (error) {
    return (
      <div className="grid min-h-screen place-items-center bg-ink-900 px-6 text-center text-fg">
        <div>
          <p className="text-sm text-bad">{error}</p>
          <a href="/login" className="mt-3 inline-block text-sm text-brand-bright underline">
            Back to sign in
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="grid min-h-screen place-items-center bg-ink-900">
      <Spinner label="Signing you in…" />
    </div>
  );
}
