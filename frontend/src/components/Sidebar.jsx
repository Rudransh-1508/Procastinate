import { NavLink, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon } from "./icons.jsx";
import { EASE } from "../motion.js";
import { useAuth } from "../AuthContext.jsx";

const nav = [
  { to: "/app", label: "Dashboard", icon: Icon.Dashboard, end: true },
  { to: "/app/checkin", label: "Check-in", icon: Icon.CheckIn },
  { to: "/app/query", label: "Ask", icon: Icon.Query },
  { to: "/app/profile", label: "Profile", icon: Icon.Profile },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const signOut = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <aside className="flex h-full w-[220px] shrink-0 flex-col border-r border-ink-500 bg-ink-800 px-3 py-5">
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="mb-7 px-2"
      >
        <Link to="/" className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-ink-900">
            <Icon.Brain width={18} height={18} />
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-fg">Profiler</div>
            <div className="text-[10px] uppercase tracking-wider text-fg-faint">procrastination</div>
          </div>
        </Link>
      </motion.div>

      <nav className="flex flex-1 flex-col gap-1">
        {nav.map(({ to, label, icon: I, end }, i) => (
          <NavLink key={to} to={to} end={end} className="group relative block">
            {({ isActive }) => (
              <motion.div
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, ease: EASE, delay: 0.06 + i * 0.05 }}
                className={`relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 ${
                  isActive ? "text-brand-bright" : "text-fg-muted group-hover:text-fg"
                }`}
              >
                {isActive && (
                  <motion.span
                    layoutId="activeNavPill"
                    className="absolute inset-0 rounded-lg bg-brand/15"
                    transition={{ type: "spring", stiffness: 480, damping: 40 }}
                  />
                )}
                {!isActive && (
                  <span className="absolute inset-0 rounded-lg bg-ink-700 opacity-0 transition-opacity duration-150 group-hover:opacity-100" />
                )}
                <I width={18} height={18} className="relative z-10" />
                <span className="relative z-10">{label}</span>
              </motion.div>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="mt-4 space-y-3 border-t border-ink-500 pt-3">
        {user && (
          <div className="flex items-center gap-2.5 px-2">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-ink-600 text-xs font-semibold text-fg-muted">
              {(user.email || "?")[0].toUpperCase()}
            </span>
            <span className="truncate text-xs text-fg-muted">{user.email}</span>
          </div>
        )}
        <button
          onClick={signOut}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-fg-muted transition-colors hover:bg-ink-700 hover:text-fg"
        >
          <Icon.LogOut width={17} height={17} />
          Sign out
        </button>
        <p className="px-2 text-[10px] leading-relaxed text-fg-faint">
          Local-first. Your data stays on this machine.
        </p>
      </div>
    </aside>
  );
}
