// Quick task entry + per-task event logging, so the whole loop works from the UI.
import { useEffect, useState, useCallback } from "react";
import { api } from "../api.js";
import { Panel, EmptyState } from "./ui.jsx";
import { Icon } from "./icons.jsx";

const TASK_TYPES = [
  "creative",
  "administrative",
  "technical",
  "social",
  "physical",
  "collaborative",
];
const DISPLACEMENTS = [
  "productive_procrastination",
  "entertainment_escape",
  "social_escape",
  "communication",
  "unknown",
];
const TRIGGERS = [
  "deadline_pressure",
  "broke_into_subtasks",
  "external_ask",
  "mood_shift",
  "post_win",
  "forced_start",
];
const fmt = (s) => s.charAt(0).toUpperCase() + s.slice(1).replace(/_/g, " ");

export default function TaskPanel({ onChanged }) {
  const [tasks, setTasks] = useState([]);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("administrative");
  const [est, setEst] = useState("");
  const [flag, setFlag] = useState(null);
  const [logFor, setLogFor] = useState(null);

  const load = useCallback(async () => {
    try {
      const { tasks } = await api.tasks();
      setTasks(tasks);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addTask = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    const res = await api.addTask({
      title: title.trim(),
      task_type: type,
      estimated_minutes: est ? Number(est) : null,
    });
    setFlag(res.proactive_insight || null);
    setTitle("");
    setEst("");
    await load();
  };

  return (
    <Panel
      title="Tasks & event logging"
      action={
        <span className="text-[10px] uppercase tracking-wider text-fg-faint">
          {tasks.length} total
        </span>
      }
    >
      <form onSubmit={addTask} className="space-y-2.5">
        <input
          className="input"
          placeholder="Add a task you might avoid…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <select className="input flex-1 min-w-[130px]" value={type} onChange={(e) => setType(e.target.value)}>
            {TASK_TYPES.map((t) => (
              <option key={t} value={t}>
                {fmt(t)}
              </option>
            ))}
          </select>
          <input
            className="input w-24"
            type="number"
            min="1"
            placeholder="est. min"
            value={est}
            onChange={(e) => setEst(e.target.value)}
          />
          <button className="btn-primary" type="submit">
            <Icon.Plus width={16} height={16} /> Add
          </button>
        </div>
      </form>

      {flag && (
        <div className="mt-3 flex gap-2 rounded-lg border border-clay/30 bg-clay/10 px-3 py-2.5 text-xs text-clay-soft">
          <Icon.Spark width={15} height={15} className="mt-0.5 shrink-0" />
          <span>{flag}</span>
        </div>
      )}

      <div className="mt-4 max-h-[260px] space-y-2 overflow-y-auto pr-1">
        {tasks.length === 0 ? (
          <EmptyState icon={Icon.Plus} title="No tasks yet">
            Add a task above. When it sits untouched, the profiler logs an avoidance event.
          </EmptyState>
        ) : (
          tasks.map((t) => (
            <TaskRow
              key={t.id}
              task={t}
              open={logFor === t.id}
              onToggle={() => setLogFor(logFor === t.id ? null : t.id)}
              onLogged={async () => {
                setLogFor(null);
                await load();
                onChanged?.();
              }}
            />
          ))
        )}
      </div>
    </Panel>
  );
}

function TaskRow({ task, open, onToggle, onLogged }) {
  const [delay, setDelay] = useState("");
  const [disp, setDisp] = useState("entertainment_escape");
  const [trigger, setTrigger] = useState("");
  const [energy, setEnergy] = useState("");
  const [completing, setCompleting] = useState(false);

  const submit = async (resolved) => {
    await api.logEvent({
      task_id: task.id,
      delay_hours: delay ? Number(delay) : null,
      displacement_type: disp,
      // No fabricated default — only send a trigger if you actually picked one.
      unlock_trigger: resolved ? trigger || null : null,
      energy_level: energy ? Number(energy) : null,
      delay_resolved: resolved,
    });
    await onLogged();
  };

  const complete = async () => {
    setCompleting(true);
    try {
      await api.completeTask(task.id);
      await onLogged();
    } finally {
      setCompleting(false);
    }
  };

  const isDone = task.status === "done";
  const statusTone =
    task.status === "done" ? "text-good" : task.status === "pending" ? "text-fg-muted" : "text-fg-faint";

  return (
    <div className="rounded-lg border border-ink-500 bg-ink-900">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-ink-700/60 cursor-pointer rounded-lg"
      >
        <span className="flex-1 truncate text-sm text-fg">{task.title}</span>
        <span className="chip bg-ink-600 text-fg-muted">{fmt(task.task_type || "unknown")}</span>
        <span className={`text-xs ${statusTone}`}>{task.status}</span>
      </button>

      {open && isDone && (
        <div className="border-t border-ink-500 px-3 py-3 text-xs text-good">
          Completed{task.completed_at ? ` · ${new Date(task.completed_at).toLocaleString()} IST` : ""}
        </div>
      )}

      {open && !isDone && (
        <div className="space-y-2.5 border-t border-ink-500 px-3 py-3">
          <div className="flex flex-wrap gap-2">
            <input
              className="input w-28"
              type="number"
              placeholder="delay hrs"
              value={delay}
              onChange={(e) => setDelay(e.target.value)}
            />
            <select className="input flex-1 min-w-[150px]" value={disp} onChange={(e) => setDisp(e.target.value)}>
              {DISPLACEMENTS.map((d) => (
                <option key={d} value={d}>
                  {fmt(d)}
                </option>
              ))}
            </select>
            <input
              className="input w-24"
              type="number"
              min="1"
              max="5"
              placeholder="energy"
              value={energy}
              onChange={(e) => setEnergy(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <select className="input flex-1 min-w-[150px]" value={trigger} onChange={(e) => setTrigger(e.target.value)}>
              <option value="">unlock trigger (if resolved)…</option>
              {TRIGGERS.map((tr) => (
                <option key={tr} value={tr}>
                  {fmt(tr)}
                </option>
              ))}
            </select>
            <button className="btn-ghost" onClick={() => submit(false)}>
              Log avoidance
            </button>
            <button className="btn-primary" onClick={() => submit(true)}>
              Mark started
            </button>
          </div>
          <div className="border-t border-ink-600 pt-2.5">
            <button
              className="btn-ghost w-full justify-center text-good hover:bg-good/10"
              onClick={complete}
              disabled={completing}
            >
              <Icon.Check width={15} height={15} />
              {completing ? "Completing…" : "Complete task"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
