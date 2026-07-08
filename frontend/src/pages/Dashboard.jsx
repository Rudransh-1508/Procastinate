import { useEffect, useState, useCallback } from "react";
import { api } from "../api.js";
import { Panel, StatCard, ConfidenceBadge, Spinner } from "../components/ui.jsx";
import { Icon } from "../components/icons.jsx";
import TemporalHeatmap from "../components/TemporalHeatmap.jsx";
import AvoidanceChart from "../components/AvoidanceChart.jsx";
import DisplacementDonut from "../components/DisplacementDonut.jsx";
import TriggerEffectiveness from "../components/TriggerEffectiveness.jsx";
import TaskPanel from "../components/TaskPanel.jsx";

const fmt = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ") : "—");

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      const d = await api.dashboard();
      setData(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onSync = async () => {
    setBusy(true);
    try {
      await api.sync();
      await api.refreshProfile();
      await load();
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="grid h-64 place-items-center">
        <Spinner label="Loading your profile…" />
      </div>
    );
  }

  const status = data?.status || {};
  const disp = data?.displacement_distribution || {};
  const dominantDisp = Object.entries(disp).sort(
    (a, b) => (b[1].frequency || 0) - (a[1].frequency || 0)
  )[0]?.[0];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-fg">Dashboard</h1>
          <p className="mt-1 text-sm text-fg-muted">
            Your personal procrastination model — it gets sharper the more you log.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ConfidenceBadge level={status.profile_confidence} />
          <button className="btn-ghost" onClick={onSync} disabled={busy}>
            <Icon.Refresh width={16} height={16} className={busy ? "animate-spin" : ""} />
            {busy ? "Syncing…" : "Sync & refresh"}
          </button>
        </div>
      </header>

      {error && (
        <div className="panel border-bad/40 bg-bad/10 px-4 py-3 text-sm text-bad">
          Couldn’t reach the API ({error}). Is the backend running on :8000?
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard index={0} label="Events logged" value={status.total_events ?? 0} tone="brand" />
        <StatCard index={1} label="Tasks tracked" value={status.total_tasks ?? 0} />
        <StatCard
          index={2}
          label="Top displacement"
          value={dominantDisp ? fmt(dominantDisp) : "—"}
          tone="clay"
          sub={dominantDisp ? "where avoided time goes" : "no data yet"}
        />
        <StatCard
          index={3}
          label="To high confidence"
          value={status.events_until_high_confidence ?? 50}
          sub="more events"
        />
      </div>

      {/* Heatmap full width */}
      <Panel index={4} title="Temporal pattern · when you avoid">
        <TemporalHeatmap data={data?.temporal_heatmap} />
      </Panel>

      {/* Two-up charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel index={5} title="Avoidance rate by task type">
          <AvoidanceChart data={data?.avoidance_by_type} />
        </Panel>
        <Panel index={6} title="Displacement signature">
          <DisplacementDonut data={data?.displacement_distribution} />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel index={7} title="Unlock triggers · what gets you started">
          <TriggerEffectiveness data={data?.trigger_effectiveness} />
        </Panel>
        <TaskPanel onChanged={onSync} />
      </div>
    </div>
  );
}
