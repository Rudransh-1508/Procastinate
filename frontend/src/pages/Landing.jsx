import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import AuroraBackground from "../components/AuroraBackground.jsx";
import { Icon } from "../components/icons.jsx";
import { EASE } from "../motion.js";

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE } },
};

const FEATURES = [
  {
    icon: Icon.List,
    title: "Task list tracking",
    body: "Todoist, a plain-text file, or manual entry. It quietly notes what slipped and for how long.",
    tone: "brand",
    span: "md:col-span-2",
  },
  {
    icon: Icon.Activity,
    title: "Passive activity",
    body: "Optional ActivityWatch link reveals what you did instead — your displacement signature.",
    tone: "clay",
  },
  {
    icon: Icon.CheckIn,
    title: "2-minute check-ins",
    body: "Talk normally. A Groq LLM extracts energy, stress, and the emotion it can't infer.",
    tone: "ochre",
  },
  {
    icon: Icon.Chart,
    title: "Real statistics",
    body: "scipy + numpy compute avoidance rates, temporal clusters, and context correlations — no LLM guessing.",
    tone: "brand",
  },
  {
    icon: Icon.Brain,
    title: "A reasoning agent",
    body: "Ask why you avoid a task type. It queries your real data, then proposes causal hypotheses.",
    tone: "clay",
    span: "md:col-span-2",
  },
];

const STEPS = [
  { n: "01", title: "It watches quietly", body: "Task delays, activity, and check-ins flow into one local SQLite model — no nagging." },
  { n: "02", title: "It finds patterns", body: "The stats engine surfaces when, how, and what-instead — clustered and correlated." },
  { n: "03", title: "It explains", body: "The agent turns numbers into specific, non-obvious hypotheses about your avoidance." },
];

const MARQUEE = [
  "task delays", "displacement signature", "temporal heatmap", "energy & stress",
  "unlock triggers", "causal hypotheses", "local-first", "avoidance rate",
];

const toneMap = {
  brand: "text-brand-bright",
  clay: "text-clay-soft",
  ochre: "text-ochre-soft",
};

export default function Landing() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-ink-900 text-fg">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-white/5 bg-ink-900/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand text-ink-900">
              <Icon.Brain width={18} height={18} />
            </span>
            <span className="font-display text-base font-semibold">Profiler</span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-fg-muted sm:flex">
            <a href="#features" className="transition-colors hover:text-fg">Features</a>
            <a href="#how" className="transition-colors hover:text-fg">How it works</a>
            <a href="#privacy" className="transition-colors hover:text-fg">Privacy</a>
          </nav>
          <Link to="/app" className="btn-primary rounded-full px-4 py-2 text-sm">
            Open app <Icon.ArrowRight width={15} height={15} />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        <AuroraBackground />
        <div className="relative mx-auto max-w-5xl px-6 pb-24 pt-24 text-center sm:pt-32">
          <motion.div initial="hidden" animate="show" variants={fadeUp}>
            <span className="chip card-natural mx-auto mb-7 inline-flex text-fg-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              Local-first · powered by Groq
            </span>
          </motion.div>

          <motion.h1
            initial="hidden"
            animate="show"
            variants={fadeUp}
            transition={{ delay: 0.05 }}
            className="font-display text-5xl font-bold leading-[1.05] tracking-tight sm:text-7xl"
          >
            Understand <span className="text-accent">how</span> you
            <br className="hidden sm:block" /> procrastinate.
          </motion.h1>

          <motion.p
            initial="hidden"
            animate="show"
            variants={fadeUp}
            transition={{ delay: 0.12 }}
            className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-fg-muted"
          >
            A private AI agent that watches what you avoid, asks brief daily check-ins, and builds a
            personal model of <em className="text-fg not-italic">when, why, and how</em> you delay
            specific kinds of work. Not to nag — to reveal the non-obvious.
          </motion.p>

          <motion.div
            initial="hidden"
            animate="show"
            variants={fadeUp}
            transition={{ delay: 0.2 }}
            className="mt-10 flex flex-wrap items-center justify-center gap-3"
          >
            <Link to="/app" className="btn-cta">
              Open the dashboard <Icon.ArrowRight width={16} height={16} className="relative z-10" />
            </Link>
            <a href="#how" className="btn-ghost rounded-full px-5 py-3">How it works</a>
          </motion.div>

          {/* stat strip */}
          <motion.div
            initial="hidden"
            animate="show"
            variants={fadeUp}
            transition={{ delay: 0.28 }}
            className="mx-auto mt-16 grid max-w-2xl grid-cols-3 gap-4"
          >
            {[
              ["3", "data sources, fused"],
              ["100%", "on your machine"],
              ["30 days", "to real insight"],
            ].map(([v, l]) => (
              <div key={l} className="card-natural rounded-xl2 px-4 py-4">
                <div className="tnum text-2xl font-semibold text-clay">{v}</div>
                <div className="mt-1 text-xs text-fg-muted">{l}</div>
              </div>
            ))}
          </motion.div>
        </div>

        {/* marquee */}
        <div className="relative flex overflow-hidden border-y border-white/5 py-4 [mask-image:linear-gradient(to_right,transparent,black_12%,black_88%,transparent)]">
          <div className="flex shrink-0 animate-marquee items-center gap-8 pr-8">
            {[...MARQUEE, ...MARQUEE].map((w, i) => (
              <span key={i} className="flex items-center gap-8 text-sm font-medium text-fg-faint">
                {w}
                <span className="h-1 w-1 rounded-full bg-brand/60" />
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Features — bento */}
      <section id="features" className="mx-auto max-w-6xl px-6 py-24">
        <SectionHeading eyebrow="What it does" title="Three signals, one honest model" />
        <div className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className={`card-natural group rounded-xl2 p-6 transition-transform duration-200 hover:-translate-y-1 ${f.span || ""}`}
            >
              <div className={`mb-4 inline-flex rounded-lg bg-ink-700 p-2.5 ${toneMap[f.tone]}`}>
                <f.icon width={20} height={20} />
              </div>
              <h3 className="font-display text-lg font-semibold">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-fg-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="relative mx-auto max-w-6xl px-6 py-24">
        <SectionHeading eyebrow="How it works" title="Useless on day one. Fascinating by day thirty." />
        <div className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="rounded-xl2 border border-ink-500 bg-ink-800 p-6">
              <div className="font-display text-4xl font-semibold italic text-brand-bright">{s.n}</div>
              <h3 className="mt-4 font-display text-lg font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-fg-muted">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Privacy / CTA */}
      <section id="privacy" className="mx-auto max-w-6xl px-6 pb-24">
        <div className="relative overflow-hidden rounded-[24px] border border-white/10 px-8 py-16 text-center">
          <div className="absolute inset-0 bg-brand/[0.06]" />
          <AuroraBackground className="opacity-70" />
          <div className="relative">
            <span className="mx-auto mb-5 inline-flex rounded-full bg-ink-900/60 p-3 text-clay-soft ring-1 ring-white/10">
              <Icon.Lock width={22} height={22} />
            </span>
            <h2 className="mx-auto max-w-2xl font-display text-3xl font-bold sm:text-4xl">
              Your data never leaves your machine.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-fg-muted">
              Everything lives in a local SQLite file. No cloud, no third party. The agent gets smarter
              only because you're honest with it — not because anyone else is watching.
            </p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <Link to="/app" className="btn-cta">
                Start profiling <Icon.ArrowRight width={16} height={16} className="relative z-10" />
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noreferrer"
                className="btn-ghost rounded-full px-5 py-3"
              >
                <Icon.Github width={16} height={16} /> Source
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-sm text-fg-faint sm:flex-row">
          <div className="flex items-center gap-2">
            <span className="grid h-6 w-6 place-items-center rounded-md bg-brand text-ink-900">
              <Icon.Brain width={13} height={13} />
            </span>
            Procrastination Profiler
          </div>
          <p>Local-first · Your data stays on your machine.</p>
        </div>
      </footer>
    </div>
  );
}

function SectionHeading({ eyebrow, title }) {
  return (
    <div className="max-w-2xl">
      <div className="mb-3 text-xs font-semibold uppercase tracking-[0.2em] text-brand-bright">
        {eyebrow}
      </div>
      <h2 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">{title}</h2>
    </div>
  );
}
