import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { api } from "../api.js";
import { Icon } from "../components/icons.jsx";
import { bubble, EASE } from "../motion.js";

const SUGGESTIONS = [
  "Why do I keep avoiding administrative tasks?",
  "When am I most likely to procrastinate?",
  "What usually gets me to finally start?",
  "What do I do instead of working?",
];

export default function Query() {
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const ask = async (text) => {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setMessages((m) => [...m, { role: "user", text: q }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.query(q, history);
      setMessages((m) => [...m, { role: "agent", text: res.response }]);
      setHistory((h) => [...h, { role: "user", content: q }, { role: "assistant", content: res.response }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "agent", text: `Error: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col">
      <header className="mb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-fg">Ask the analyst</h1>
        <p className="mt-1 text-sm text-fg-muted">
          A pattern analyst, not a coach. It queries your real data before answering — no made-up numbers.
        </p>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto rounded-xl2 border border-ink-500 bg-ink-900/60 p-5">
        {messages.length === 0 && (
          <div className="grid h-full place-items-center">
            <div className="w-full max-w-md text-center">
              <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-full bg-brand/15 text-brand-bright">
                <Icon.Brain width={24} height={24} />
              </div>
              <p className="mb-4 text-sm text-fg-muted">Ask anything about your patterns.</p>
              <div className="grid gap-2">
                {SUGGESTIONS.map((s, i) => (
                  <motion.button
                    key={s}
                    onClick={() => ask(s)}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, ease: EASE, delay: 0.1 + i * 0.06 }}
                    whileHover={{ x: 3 }}
                    className="rounded-lg border border-ink-500 bg-ink-800 px-3.5 py-2.5 text-left text-sm text-fg-muted transition-colors hover:border-brand/50 hover:text-fg cursor-pointer"
                  >
                    {s}
                  </motion.button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <motion.div
            key={i}
            variants={bubble}
            initial="hidden"
            animate="show"
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                m.role === "user"
                  ? "rounded-br-sm bg-brand text-ink-900"
                  : "rounded-bl-sm bg-ink-700 text-fg"
              }`}
            >
              {m.text}
            </div>
          </motion.div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm bg-ink-700 px-4 py-3 text-sm text-fg-muted">
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-500 border-t-brand" />
              analyzing your data…
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="mt-4 flex items-end gap-2">
        <textarea
          className="input max-h-32 min-h-[48px] flex-1 resize-none"
          rows={1}
          placeholder="Ask about your procrastination patterns…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask();
            }
          }}
        />
        <button className="btn-primary h-[48px]" onClick={() => ask()} disabled={busy || !input.trim()}>
          <Icon.Send width={16} height={16} />
        </button>
      </div>
    </div>
  );
}
