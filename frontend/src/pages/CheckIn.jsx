import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../api.js";
import { Icon } from "../components/icons.jsx";
import { bubble, EASE } from "../motion.js";

const fmt = (s) => (s == null ? "—" : String(s).replace(/_/g, " "));

function ExtractedCard({ data }) {
  const fields = [
    ["Energy", data.energy_level != null ? `${data.energy_level}/5` : null],
    ["Stress", data.stress_level != null ? `${data.stress_level}/5` : null],
    ["Emotion", data.emotional_texture],
    ["Context", data.social_context],
    ["Sleep", data.hours_of_sleep != null ? `${data.hours_of_sleep}h` : null],
    ["Sentiment", data.sentiment],
  ].filter(([, v]) => v != null && v !== "");

  return (
    <div className="rounded-xl2 border border-ink-500 bg-ink-800 p-3.5">
      <div className="panel-title mb-2.5 flex items-center gap-1.5">
        <Icon.Spark width={13} height={13} /> What I logged
      </div>
      <div className="flex flex-wrap gap-2">
        {fields.length === 0 && <span className="text-xs text-fg-faint">No structured signals found.</span>}
        {fields.map(([k, v]) => (
          <span key={k} className="chip bg-ink-600 text-fg">
            <span className="text-fg-faint">{k}</span> {fmt(v)}
          </span>
        ))}
      </div>
      {data.reason_for_avoidance && (
        <p className="mt-3 border-t border-ink-500 pt-2.5 text-xs italic text-fg-muted">
          “{data.reason_for_avoidance}”
        </p>
      )}
    </div>
  );
}

export default function CheckIn() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    api
      .checkinPrompt("morning")
      .then((r) => setMessages([{ role: "agent", text: r.prompt }]))
      .catch(() =>
        setMessages([{ role: "agent", text: "Hey — how's it going? Anything you're avoiding today?" }])
      );
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.submitCheckin(text, "manual");
      setMessages((m) => [
        ...m,
        { role: "agent", text: "Got it — logged this and added it to your pattern.", extracted: res.extracted },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: "agent", text: `Couldn't save that (${e.message}).` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-fg">Daily check-in</h1>
        <p className="mt-1 text-sm text-fg-muted">
          Talk normally — under two minutes. The agent extracts the emotional context it can’t infer.
        </p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto rounded-xl2 border border-ink-500 bg-ink-900/60 p-5">
        {messages.map((m, i) => (
          <motion.div
            key={i}
            variants={bubble}
            initial="hidden"
            animate="show"
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className="max-w-[78%] space-y-2.5">
              <div
                className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  m.role === "user"
                    ? "rounded-br-sm bg-brand text-ink-900"
                    : "rounded-bl-sm bg-ink-700 text-fg"
                }`}
              >
                {m.text}
              </div>
              {m.extracted && (
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: EASE, delay: 0.15 }}
                >
                  <ExtractedCard data={m.extracted} />
                </motion.div>
              )}
            </div>
          </motion.div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm bg-ink-700 px-4 py-3">
              <span className="flex gap-1">
                <Dot /> <Dot d="150ms" /> <Dot d="300ms" />
              </span>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="mt-4 flex items-end gap-2">
        <textarea
          className="input max-h-32 min-h-[48px] flex-1 resize-none"
          rows={1}
          placeholder="e.g. had three back-to-back calls, exhausted 2/5, kept opening twitter instead of the report…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <button className="btn-primary h-[48px]" onClick={send} disabled={busy || !input.trim()}>
          <Icon.Send width={16} height={16} />
        </button>
      </div>
    </div>
  );
}

function Dot({ d = "0ms" }) {
  return (
    <span
      className="h-1.5 w-1.5 animate-bounce rounded-full bg-fg-muted"
      style={{ animationDelay: d }}
    />
  );
}
