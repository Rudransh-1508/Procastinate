// Horizontal bar chart: avoidance rate by task type.
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { EmptyState } from "./ui.jsx";

const fmt = (s) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");

function barColor(rate) {
  if (rate >= 0.7) return "#ff5a4d"; // coral (high avoidance)
  if (rate >= 0.45) return "#f2b544"; // amber
  return "#4fb477"; // green
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-ink-500 bg-ink-700 px-3 py-2 text-xs shadow-panel">
      <div className="font-medium text-fg">{fmt(d.type)}</div>
      <div className="mt-1 tnum text-fg-muted">
        {Math.round(d.avoidance_rate * 100)}% avoided · {d.total_events} events
      </div>
      <div className="tnum text-fg-muted">avg delay {d.avg_delay_hours}h</div>
    </div>
  );
}

export default function AvoidanceChart({ data }) {
  const rows = Object.entries(data || {})
    .map(([type, v]) => ({ type, ...v }))
    .sort((a, b) => b.avoidance_rate - a.avoidance_rate);

  if (rows.length === 0) {
    return (
      <EmptyState title="No task-type data yet">
        Avoidance rates per task type (creative, administrative, technical…) appear here once events
        are linked to tasks.
      </EmptyState>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(140, rows.length * 46)}>
      <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <XAxis
          type="number"
          domain={[0, 1]}
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
          tick={{ fill: "#a3a3a3", fontSize: 11 }}
          axisLine={{ stroke: "#3a3a3a" }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="type"
          tickFormatter={fmt}
          tick={{ fill: "#ededed", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={96}
        />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.03)" }} content={<CustomTooltip />} />
        <Bar dataKey="avoidance_rate" radius={[0, 5, 5, 0]} barSize={18}>
          {rows.map((r, i) => (
            <Cell key={i} fill={barColor(r.avoidance_rate)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
