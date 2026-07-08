// Donut chart: displacement signature (what you do instead).
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState } from "./ui.jsx";

const COLORS = {
  productive_procrastination: "#ff5a4d", // coral
  entertainment_escape: "#f2b544", // amber
  social_escape: "#8a97a3", // stone
  communication: "#4fb477", // green
  work: "#ff8a65", // soft coral
  physical_escape: "#c084fc", // violet (rare, keep distinct)
  unknown: "#5c5c5c", // neutral grey
};
const fmt = (s) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-ink-500 bg-ink-700 px-3 py-2 text-xs shadow-panel">
      <div className="font-medium text-fg">{fmt(d.name)}</div>
      <div className="mt-1 tnum text-fg-muted">{Math.round(d.frequency * 100)}% of events</div>
      {d.avg_duration_minutes > 0 && (
        <div className="tnum text-fg-muted">avg {d.avg_duration_minutes} min</div>
      )}
    </div>
  );
}

export default function DisplacementDonut({ data }) {
  const rows = Object.entries(data || {}).map(([name, v]) => ({ name, ...v }));
  if (rows.length === 0) {
    return (
      <EmptyState title="No displacement data yet">
        When ActivityWatch is running (or events are logged), this shows the mix of what you do
        instead — productive procrastination, entertainment, social escape…
      </EmptyState>
    );
  }

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div className="h-[180px] w-[180px] shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={rows}
              dataKey="frequency"
              nameKey="name"
              innerRadius={52}
              outerRadius={84}
              paddingAngle={2}
              stroke="none"
            >
              {rows.map((r, i) => (
                <Cell key={i} fill={COLORS[r.name] || "#4b5366"} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex-1 space-y-2 self-stretch">
        {rows
          .sort((a, b) => b.frequency - a.frequency)
          .map((r) => (
            <li key={r.name} className="flex items-center gap-2.5 text-sm">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ backgroundColor: COLORS[r.name] || "#4b5366" }}
              />
              <span className="flex-1 text-fg-muted">{fmt(r.name)}</span>
              <span className="tnum font-medium text-fg">{Math.round(r.frequency * 100)}%</span>
            </li>
          ))}
      </ul>
    </div>
  );
}
