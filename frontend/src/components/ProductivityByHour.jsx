// Completion rate + energy, both bucketed by hour-of-day — answers "when
// am I actually productive" rather than just "when do I avoid".
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { EmptyState } from "./ui.jsx";
import { Icon } from "./icons.jsx";

const hourLabel = (h) => {
  if (h === 0) return "12am";
  if (h === 12) return "12pm";
  return h < 12 ? `${h}am` : `${h - 12}pm`;
};

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  if (!d.n) return null;
  return (
    <div className="rounded-lg border border-ink-500 bg-ink-700 px-3 py-2 text-xs shadow-panel">
      <div className="font-medium text-fg">{hourLabel(d.hour)}</div>
      <div className="mt-1 tnum text-fg-muted">{Math.round(d.completion_rate * 100)}% completed on time</div>
      {d.energy > 0 && <div className="tnum text-fg-muted">avg energy {d.energy}/5</div>}
      <div className="tnum text-fg-faint">{d.n} session{d.n === 1 ? "" : "s"}</div>
    </div>
  );
}

export default function ProductivityByHour({ data }) {
  const completion = data?.completion_rate_by_hour || [];
  const energy = data?.energy_by_hour || [];
  const counts = data?.counts_by_hour || [];
  const n = data?.n || 0;

  if (n === 0) {
    return (
      <EmptyState icon={Icon.Activity} title="No sessions closed out yet">
        Once you've completed a few sessions, this shows which hours you actually finish on time
        vs. drift — and how your self-reported energy tracks across the day.
      </EmptyState>
    );
  }

  const rows = Array.from({ length: 24 }, (_, h) => ({
    hour: h,
    completion_rate: completion[h] || 0,
    energy: energy[h] || 0,
    n: counts[h] || 0,
  }));

  const peakHour = data?.peak_hour;
  const troughHour = data?.trough_hour;

  return (
    <div>
      {peakHour != null && troughHour != null && peakHour !== troughHour && (
        <p className="mb-3 text-xs text-fg-muted">
          You complete{" "}
          <span className="text-good">{Math.round((completion[peakHour] || 0) * 100)}%</span> of
          sessions started around <span className="text-fg">{hourLabel(peakHour)}</span>, vs.{" "}
          <span className="text-bad">{Math.round((completion[troughHour] || 0) * 100)}%</span> around{" "}
          <span className="text-fg">{hourLabel(troughHour)}</span>.
        </p>
      )}
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={rows} margin={{ left: -12, right: 8, top: 4, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#3a3a3a" strokeOpacity={0.4} />
          <XAxis
            dataKey="hour"
            tickFormatter={hourLabel}
            interval={2}
            tick={{ fill: "#a3a3a3", fontSize: 10 }}
            axisLine={{ stroke: "#3a3a3a" }}
            tickLine={false}
          />
          <YAxis
            yAxisId="rate"
            domain={[0, 1]}
            tickFormatter={(v) => `${Math.round(v * 100)}%`}
            tick={{ fill: "#a3a3a3", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <YAxis yAxisId="energy" orientation="right" domain={[0, 5]} hide />
          <Tooltip cursor={{ fill: "rgba(255,255,255,0.03)" }} content={<CustomTooltip />} />
          <Bar yAxisId="rate" dataKey="completion_rate" fill="#4fb477" radius={[3, 3, 0, 0]} barSize={10} />
          <Line
            yAxisId="energy"
            dataKey="energy"
            stroke="#f2b544"
            strokeWidth={2}
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="mt-2 flex items-center gap-4 text-[10px] text-fg-faint">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-sm bg-good" /> completion rate
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-0.5 w-3 bg-ochre" /> avg energy
        </span>
      </div>
    </div>
  );
}
