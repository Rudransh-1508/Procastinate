# Stitch MCP — setup

[Google Stitch](https://stitch.withgoogle.com) is Google Labs' Gemini-powered UI design tool. Its
remote MCP server lets an AI agent read your Stitch designs (component structure, color tokens,
`DESIGN.md`) and generate matching code.

This repo already contains the config at [`.mcp.json`](.mcp.json):

```json
{
  "mcpServers": {
    "stitch": {
      "type": "http",
      "url": "https://stitch.googleapis.com/mcp",
      "headers": { "Authorization": "Bearer ${STITCH_API_KEY}" }
    }
  }
}
```

## To activate it

1. **Get a Stitch API key** — open <https://stitch.withgoogle.com>, sign in, and follow the official
   MCP setup to obtain an API key.
2. **Expose it to Claude Code** — export the key before launching Claude Code:
   ```bash
   export STITCH_API_KEY="your_key_here"
   ```
3. **Restart Claude Code** in this project directory. On startup it reads `.mcp.json`, prompts you to
   approve the `stitch` server, and exposes tools like `create_project`,
   `generate_screen_from_text`, `list_projects`, and `get_screen`.

> Claude Code only loads MCP servers **at startup**, so the server can't be used in the session where
> it was added — a restart is required. After restart, ask me to "use Stitch to design X" and I can
> call the `mcp__stitch__*` tools.

*Sources: [Google Codelab: Design-to-Code with Stitch MCP](https://codelabs.developers.google.com/design-to-code-with-antigravity-stitch), [piyushcreates/stitch-mcp](https://github.com/piyushcreates/stitch-mcp), [PulseMCP](https://www.pulsemcp.com/servers/kargatharaakash-google-stitch).*

---

# 21st.dev Magic MCP — setup

[21st.dev](https://21st.dev) is a registry of polished, animated React + Tailwind components. Its
**Magic MCP** lets an agent generate/insert those components on demand. It's already registered in
[`.mcp.json`](.mcp.json) as `magic`:

```json
"magic": {
  "command": "npx",
  "args": ["-y", "@21st-dev/magic@latest"],
  "env": { "API_KEY": "${TWENTYFIRST_API_KEY}" }
}
```

## To activate it

1. Get an API key at <https://21st.dev/magic/console>.
2. Export it, then restart Claude Code in this project:
   ```bash
   export TWENTYFIRST_API_KEY="your_key_here"
   ```
3. On restart, approve the `magic` server. Then ask me to "add a 21st.dev hero/pricing/testimonial
   component" and I'll call `mcp__magic__*`.

> Same startup-only limitation as Stitch: a freshly-added MCP can't be used in the session that added
> it. The current landing page was built by hand in **21st.dev's component style** (aurora gradient
> background, bento grid, shimmer buttons, marquee) so you get the look now, without waiting.

