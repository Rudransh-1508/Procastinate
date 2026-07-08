// What finally breaks the avoidance — unlock-trigger frequency + avg delay before it.
import { motion } from "framer-motion";
import { EmptyState } from "./ui.jsx";
import { Icon } from "./icons.jsx";
import { EASE } from "../motion.js";

const fmt = (s) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");

export default function TriggerEffectiveness({ data }) {
  const rows = Object.entries(data || {})
    .map(([trigger, v]) => ({ trigger, ...v }))
    .sort((a, b) => b.times_used - a.times_used);

  if (rows.length === 0) {
    return (
      <EmptyState icon={Icon.Spark} title="No unlock triggers yet">
        When you record what finally got you started (a deadline, breaking it into subtasks, an
        external ask…), the most effective triggers rank here.
      </EmptyState>
    );
  }

  const maxUsed = Math.max(...rows.map((r) => r.times_used), 1);

  return (
    <ul className="space-y-3">
      {rows.map((r, i) => (
        <li key={r.trigger}>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-fg">{fmt(r.trigger)}</span>
            <span className="tnum text-xs text-fg-muted">
              {r.times_used}× · {r.avg_delay_before_trigger}h delay
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-ink-600">
            <motion.div
              className="h-full origin-left rounded-full bg-gradient-to-r from-brand to-brand-bright"
              style={{ width: `${(r.times_used / maxUsed) * 100}%` }}
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ duration: 0.6, ease: EASE, delay: 0.1 + i * 0.06 }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
