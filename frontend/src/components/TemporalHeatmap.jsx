// 7 days × 24 hours avoidance-intensity grid.
import { motion } from "framer-motion";
import { EmptyState } from "./ui.jsx";
import { Icon } from "./icons.jsx";
import { EASE } from "../motion.js";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

// charcoal-to-coral ramp keyed on normalized intensity (0..1 of max cell)
function cellColor(v) {
  if (v <= 0) return "#1c1c1c";
  // interpolate from charcoal → stone → amber → coral as intensity rises
  const stops = [
    [0.0, [28, 28, 28]],
    [0.25, [90, 90, 100]], // cool stone
    [0.5, [138, 151, 163]], // stone
    [0.75, [242, 181, 68]], // amber
    [1.0, [255, 90, 77]], // coral (hot)
  ];
  let lo = stops[0], hi = stops[stops.length - 1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (v >= stops[i][0] && v <= stops[i + 1][0]) {
      lo = stops[i];
      hi = stops[i + 1];
      break;
    }
  }
  const t = (v - lo[0]) / (hi[0] - lo[0] || 1);
  const c = lo[1].map((ch, i) => Math.round(ch + (hi[1][i] - ch) * t));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

export default function TemporalHeatmap({ data }) {
  const counts = data?.counts;
  const total = data?.total_events || 0;
  if (!counts || total === 0) {
    return (
      <EmptyState icon={Icon.Clock} title="No temporal pattern yet">
        Once avoidance events accumulate, this grid lights up to show which days and hours you most
        often delay work.
      </EmptyState>
    );
  }

  const max = Math.max(...counts.flat(), 1);
  const peakDay = data.peak_day != null ? DAYS[data.peak_day] : null;
  const peakHour = data.peak_hour;

  return (
    <div>
      <div className="overflow-x-auto pb-1">
        <div className="min-w-[640px]">
          {/* hour axis */}
          <div className="mb-1 grid grid-cols-[34px_repeat(24,1fr)] gap-[3px]">
            <div />
            {HOURS.map((h) => (
              <div key={h} className="text-center text-[9px] tnum text-fg-faint">
                {h % 3 === 0 ? h : ""}
              </div>
            ))}
          </div>
          {counts.map((row, d) => (
            <motion.div
              key={d}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, ease: EASE, delay: d * 0.05 }}
              className="mb-[3px] grid grid-cols-[34px_repeat(24,1fr)] items-center gap-[3px]"
            >
              <div className="text-[10px] font-medium text-fg-muted">{DAYS[d]}</div>
              {row.map((v, h) => {
                const intensity = v / max;
                return (
                  <div
                    key={h}
                    title={`${DAYS[d]} ${String(h).padStart(2, "0")}:00 — ${v} event${v === 1 ? "" : "s"}`}
                    className="aspect-square w-full rounded-[3px] transition-transform duration-150 hover:scale-[1.35] hover:ring-1 hover:ring-white/30"
                    style={{ backgroundColor: cellColor(intensity) }}
                  />
                );
              })}
            </motion.div>
          ))}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-fg-muted">
        <div className="flex items-center gap-2">
          <span>Less</span>
          <div className="flex gap-[3px]">
            {[0, 0.25, 0.5, 0.75, 1].map((s) => (
              <span key={s} className="h-3 w-3 rounded-[2px]" style={{ backgroundColor: cellColor(s) }} />
            ))}
          </div>
          <span>More</span>
        </div>
        {peakDay != null && (
          <div>
            Peak: <span className="text-fg">{peakDay}</span> around{" "}
            <span className="tnum text-fg">{String(peakHour).padStart(2, "0")}:00</span>
          </div>
        )}
      </div>
    </div>
  );
}
