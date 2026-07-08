// Shared presentational primitives (motion-enhanced).
import { motion } from "framer-motion";
import { Icon } from "./icons.jsx";
import AnimatedNumber from "./AnimatedNumber.jsx";
import { EASE } from "../motion.js";

export function Panel({ title, action, children, className = "", index = 0 }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.34, ease: EASE, delay: index * 0.05 }}
      className={`panel p-5 ${className}`}
    >
      {(title || action) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="panel-title">{title}</h2>}
          {action}
        </header>
      )}
      {children}
    </motion.section>
  );
}

export function StatCard({ label, value, sub, tone = "default", index = 0 }) {
  const toneClass = {
    default: "text-fg",
    brand: "text-brand-bright",
    clay: "text-clay-soft",
    ochre: "text-ochre-soft",
    good: "text-good",
    bad: "text-bad",
  }[tone];

  const isNumber = typeof value === "number";
  const isText = typeof value === "string" && /[a-z]/i.test(value);

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.34, ease: EASE, delay: index * 0.06 }}
      whileHover={{ y: -3 }}
      className="panel px-5 py-4 transition-colors hover:border-ink-500/80 hover:bg-ink-700/40"
    >
      <div className="panel-title">{label}</div>
      <div
        className={`mt-2 font-semibold ${toneClass} ${
          isText ? "text-xl leading-tight break-words" : "tnum text-3xl leading-none"
        }`}
      >
        {isNumber ? <AnimatedNumber value={value} /> : value}
      </div>
      {sub && <div className="mt-1.5 text-xs text-fg-muted">{sub}</div>}
    </motion.div>
  );
}

const confidenceMap = {
  low: { label: "Low confidence", cls: "bg-bad/15 text-bad" },
  medium: { label: "Medium confidence", cls: "bg-warn/15 text-warn" },
  high: { label: "High confidence", cls: "bg-good/15 text-good" },
};

export function ConfidenceBadge({ level }) {
  const c = confidenceMap[level] || confidenceMap.low;
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: EASE }}
      className={`chip ${c.cls}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {c.label}
    </motion.span>
  );
}

export function EmptyState({ icon: IconComp = Icon.Spark, title, children }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-ink-500 px-6 py-10 text-center">
      <motion.div
        initial={{ scale: 0.85, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="mb-3 rounded-full bg-ink-700 p-3 text-fg-muted"
      >
        <IconComp width={22} height={22} />
      </motion.div>
      <p className="text-sm font-medium text-fg">{title}</p>
      {children && <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-fg-muted">{children}</p>}
    </div>
  );
}

export function Spinner({ label }) {
  return (
    <div className="flex items-center gap-2 text-sm text-fg-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-ink-500 border-t-brand" />
      {label}
    </div>
  );
}
