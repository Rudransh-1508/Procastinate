import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { api } from "../api.js";
import { Panel, StatCard, ConfidenceBadge, EmptyState, Spinner } from "../components/ui.jsx";
import { Icon } from "../components/icons.jsx";
import { EASE } from "../motion.js";

const fmt = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : "—");

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [report, setReport] = useState(null);
  const [reportBusy, setReportBusy] = useState(false);
  const [refreshBusy, setRefreshBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const p = await api.profile();
      setProfile(p);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const refresh = async () => {
    setRefreshBusy(true);
    try {
      await api.refreshProfile();
      await load();
    } finally {
      setRefreshBusy(false);
    }
  };

  const genReport = async () => {
    setReportBusy(true);
    setReport(null);
    try {
      const r = await api.weeklyReport();
      setReport(r.report);
    } catch (e) {
      setReport(`Couldn't generate report: ${e.message}`);
    } finally {
      setReportBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="grid h-64 place-items-center">
        <Spinner label="Loading profile…" />
      </div>
    );
  }

  const hasModel = profile && profile.total_events_analyzed != null;
  const hypotheses = Array.isArray(profile?.active_hypotheses) ? profile.active_hypotheses : [];
  const avoidance = profile?.avoidance_by_type || {};
  const updated = profile?.updated_at ? `${new Date(profile.updated_at).toLocaleString()} IST` : "never";

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-fg">Your model</h1>
          <p className="mt-1 text-sm text-fg-muted">
            The evolving picture of how you avoid work. Updated {updated}.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {hasModel && <ConfidenceBadge level={profile.profile_confidence} />}
          <button className="btn-ghost" onClick={refresh} disabled={refreshBusy}>
            <Icon.Refresh width={16} height={16} className={refreshBusy ? "animate-spin" : ""} />
            Recompute
          </button>
        </div>
      </header>

      {!hasModel ? (
        <Panel>
          <EmptyState icon={Icon.Brain} title="No model yet">
            Log a few tasks and avoidance events (from the Dashboard), then hit “Recompute”. The model
            becomes meaningful around 20 events and confident at 50.
          </EmptyState>
        </Panel>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
            <StatCard label="Events analyzed" value={profile.total_events_analyzed ?? 0} tone="brand" />
            <StatCard label="Confidence" value={fmt(profile.profile_confidence)} tone="ochre" />
            <StatCard label="Task types seen" value={Object.keys(avoidance).length} />
          </div>

          <Panel title="Active hypotheses" action={<span className="text-[10px] uppercase tracking-wider text-fg-faint">agent-generated</span>}>
            {hypotheses.length === 0 ? (
              <EmptyState icon={Icon.Spark} title="No hypotheses yet">
                Ask the analyst a few questions, or generate a weekly report — confirmed patterns get
                promoted into your model here.
              </EmptyState>
            ) : (
              <ul className="space-y-2.5">
                {hypotheses.map((h, i) => (
                  <li key={i} className="flex gap-2.5 text-sm text-fg">
                    <Icon.Spark width={15} height={15} className="mt-0.5 shrink-0 text-brand-bright" />
                    {h}
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Avoidance by task type">
            <div className="space-y-3">
              {Object.entries(avoidance)
                .sort((a, b) => (b[1].avoidance_rate || 0) - (a[1].avoidance_rate || 0))
                .map(([type, v]) => (
                  <div key={type}>
                    <div className="mb-1 flex justify-between text-sm">
                      <span className="text-fg">{fmt(type)}</span>
                      <span className="tnum text-fg-muted">
                        {Math.round((v.avoidance_rate || 0) * 100)}% · avg {v.avg_delay_hours}h
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-ink-600">
                      <motion.div
                        className="h-full origin-left rounded-full bg-gradient-to-r from-brand to-ochre"
                        style={{ width: `${(v.avoidance_rate || 0) * 100}%` }}
                        initial={{ scaleX: 0 }}
                        animate={{ scaleX: 1 }}
                        transition={{ duration: 0.6, ease: EASE }}
                      />
                    </div>
                  </div>
                ))}
            </div>
          </Panel>
        </>
      )}

      <Panel
        title="Weekly insight report"
        action={
          <button className="btn-ghost" onClick={genReport} disabled={reportBusy}>
            <Icon.Spark width={16} height={16} />
            {reportBusy ? "Generating…" : "Generate"}
          </button>
        }
      >
        {reportBusy ? (
          <Spinner label="The analyst is writing your report…" />
        ) : report ? (
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-fg">{report}</div>
        ) : (
          <EmptyState icon={Icon.Brain} title="No report generated yet">
            Generate a curious-scientist summary of your week — the 2–3 strongest patterns and a causal
            hypothesis, grounded in your logged data.
          </EmptyState>
        )}
      </Panel>
    </div>
  );
}
