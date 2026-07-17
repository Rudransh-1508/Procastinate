// Natural-language plan -> actual logging. This is the daily-use loop:
// state a plan in plain words, get a time-boxed session, close it out
// (any time — early, on time, late, or not at all) in plain words too.
import { useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api.js";
import { Panel, EmptyState, Spinner } from "../components/ui.jsx";
import { Icon } from "../components/icons.jsx";
import { EASE, container, item } from "../motion.js";

const fmt = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : "—");

const OUTCOME_STYLE = {
  early: "bg-good/15 text-good",
  on_time: "bg-brand/15 text-brand-bright",
  delayed: "bg-ochre/15 text-ochre-soft",
  not_done: "bg-bad/15 text-bad",
};

function OutcomeBadge({ outcome }) {
  if (!outcome) return null;
  return <span className={`chip ${OUTCOME_STYLE[outcome] || "bg-ink-600 text-fg-muted"}`}>{fmt(outcome)}</span>;
}

function fmtDuration(mins) {
  if (mins == null) return "";
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  if (h && m) return `${h}h ${m}m`;
  if (h) return `${h}h`;
  return `${m}m`;
}

function useCountdown(plannedEnd) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!plannedEnd) return null;
  // planned_end is a naive IST string; treat it as local wall-clock (matches
  // browser's own clock as long as the browser is IST, which is the app's
  // stated assumption throughout).
  const end = new Date(plannedEnd).getTime();
  const diffMs = end - now;
  const overdue = diffMs < 0;
  const abs = Math.abs(diffMs);
  const h = Math.floor(abs / 3600000);
  const m = Math.floor((abs % 3600000) / 60000);
  const s = Math.floor((abs % 60000) / 1000);
  const label = h > 0 ? `${h}h ${m}m` : m > 0 ? `${m}m ${s}s` : `${s}s`;
  return { label, overdue };
}

export default function Sessions() {
  const [active, setActive] = useState(undefined); // undefined = loading, null = none
  const [history, setHistory] = useState([]);
  const [planText, setPlanText] = useState("");
  const [closeoutText, setCloseoutText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [justClosed, setJustClosed] = useState(null);
  const closeoutRef = useRef(null);

  // React 18 StrictMode double-invokes effects in dev, and this component's
  // own action handlers (start/closeout) can race an in-flight background
  // load(). A monotonic sequence number lets us drop any load() response
  // that resolves after a newer write has already set fresher state, instead
  // of letting a stale "no active session" response clobber it.
  const loadSeq = useRef(0);

  const load = useCallback(async () => {
    const mySeq = ++loadSeq.current;
    try {
      const [a, h] = await Promise.all([api.activeSession(), api.sessions()]);
      if (mySeq !== loadSeq.current) return; // superseded by a newer load/action
      setActive(a);
      setHistory(h.sessions || []);
    } catch (e) {
      if (mySeq !== loadSeq.current) return;
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const countdown = useCountdown(active?.planned_end);

  const startSession = async (e) => {
    e.preventDefault();
    if (!planText.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const session = await api.startSession(planText.trim());
      loadSeq.current++; // supersede any in-flight background load()
      setPlanText("");
      setActive(session);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const closeout = async (e) => {
    e.preventDefault();
    if (!closeoutText.trim() || busy || !active) return;
    setBusy(true);
    setError(null);
    try {
      const closed = await api.closeoutSession(active.id, closeoutText.trim());
      loadSeq.current++; // supersede any in-flight background load()
      setCloseoutText("");
      setJustClosed(closed);
      setActive(null);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (active === undefined) {
    return (
      <div className="grid h-64 place-items-center">
        <Spinner label="Loading your session…" />
      </div>
    );
  }

  const pending = active?.status === "pending_closeout";

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-fg">Sessions</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Say what you're about to do, then say how it actually went. No dropdowns.
        </p>
      </header>

      {error && (
        <div className="panel border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">{error}</div>
      )}

      <AnimatePresence mode="wait">
        {!active && (
          <motion.div key="start" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Panel title="What's the plan?">
              <form onSubmit={startSession} className="flex gap-2">
                <input
                  className="input flex-1"
                  placeholder="e.g. studying DSA for 3 hours"
                  value={planText}
                  onChange={(e) => setPlanText(e.target.value)}
                  autoFocus
                />
                <button className="btn-primary" type="submit" disabled={busy || !planText.trim()}>
                  <Icon.Send width={16} height={16} />
                  {busy ? "Starting…" : "Start"}
                </button>
              </form>
              <p className="mt-2.5 text-xs text-fg-faint">
                Say what you're doing and for how long — the duration and category are picked up
                automatically. The clock starts now.
              </p>
            </Panel>
          </motion.div>
        )}

        {active && (
          <motion.div key="active" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Panel>
              <div className={`rounded-xl2 border p-5 ${pending ? "border-ochre/40 bg-ochre/5" : "border-ink-500"}`}>
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${pending ? "bg-ochre animate-pulse" : "bg-good animate-pulse"}`} />
                      <span className="text-xs font-semibold uppercase tracking-wider text-fg-faint">
                        {pending ? "Time's up" : "In progress"}
                      </span>
                    </div>
                    <h2 className="mt-1.5 font-display text-xl font-semibold text-fg">{active.title}</h2>
                    <p className="mt-0.5 text-xs text-fg-muted">
                      Planned {fmtDuration(active.planned_duration_minutes)} · {fmt(active.task_type)}
                    </p>
                  </div>
                  {countdown && (
                    <div className="text-right">
                      <div className={`tnum text-2xl font-semibold ${countdown.overdue ? "text-ochre-soft" : "text-fg"}`}>
                        {countdown.label}
                      </div>
                      <div className="text-[10px] uppercase tracking-wider text-fg-faint">
                        {countdown.overdue ? "over" : "left"}
                      </div>
                    </div>
                  )}
                </div>

                <p className="mt-4 text-sm">
                  {pending ? (
                    <span className="text-ochre-soft">
                      Your session ended {countdown?.label} ago — what happened?
                    </span>
                  ) : (
                    <span className="text-fg-muted">Close out any time — even before time's up.</span>
                  )}
                </p>

                <form onSubmit={closeout} className="mt-3 flex gap-2">
                  <input
                    ref={closeoutRef}
                    className="input flex-1"
                    placeholder="e.g. got distracted by texts, did it 40 min late"
                    value={closeoutText}
                    onChange={(e) => setCloseoutText(e.target.value)}
                  />
                  <button className="btn-primary" type="submit" disabled={busy || !closeoutText.trim()}>
                    <Icon.Check width={16} height={16} />
                    {busy ? "Closing…" : "Close out"}
                  </button>
                </form>
              </div>
            </Panel>
          </motion.div>
        )}
      </AnimatePresence>

      {justClosed && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: EASE }}
          className="panel flex items-start gap-3 border-good/30 bg-good/5 p-4"
        >
          <Icon.Check width={18} height={18} className="mt-0.5 shrink-0 text-good" />
          <div className="flex-1 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium text-fg">{justClosed.title}</span>
              <OutcomeBadge outcome={justClosed.outcome} />
            </div>
            {justClosed.reason && <p className="mt-1 text-xs text-fg-muted">{justClosed.reason}</p>}
          </div>
          <button className="text-xs text-fg-faint hover:text-fg" onClick={() => setJustClosed(null)}>
            dismiss
          </button>
        </motion.div>
      )}

      <Panel title="History" action={<span className="text-[10px] uppercase tracking-wider text-fg-faint">{history.length} total</span>}>
        {history.length === 0 ? (
          <EmptyState icon={Icon.Clock} title="No sessions yet">
            Start one above. Once you close it out, it shows up here with what actually happened.
          </EmptyState>
        ) : (
          <motion.ul variants={container} initial="hidden" animate="show" className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
            {history
              .filter((s) => s.status === "closed")
              .map((s) => (
                <motion.li
                  key={s.id}
                  variants={item}
                  className="flex items-center gap-3 rounded-lg border border-ink-500 bg-ink-900 px-3 py-2.5"
                >
                  <span className="flex-1 min-w-0">
                    <span className="block truncate text-sm text-fg">{s.title}</span>
                    <span className="block text-xs text-fg-faint">
                      {fmtDuration(s.planned_duration_minutes)} planned
                      {s.delay_minutes > 0 ? ` · ${fmtDuration(s.delay_minutes)} late` : ""}
                    </span>
                  </span>
                  <span className="chip bg-ink-600 text-fg-muted">{fmt(s.task_type)}</span>
                  <OutcomeBadge outcome={s.outcome} />
                </motion.li>
              ))}
          </motion.ul>
        )}
      </Panel>
    </div>
  );
}
