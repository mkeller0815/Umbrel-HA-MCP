# Home Assistant MCP Server for Umbrel

A community app store package that brings the [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) Model Context Protocol server to [Umbrel](https://umbrel.com). Once installed, AI assistants like Claude, ChatGPT, and Gemini can control your smart home devices, query states, manage automations, and execute services — all through natural language.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io) is an open standard that lets AI assistants talk to external tools and services. Ha-mcp implements MCP on top of the Home Assistant API, exposing 85+ tools that cover everything from switching a light to editing automations.

## Prerequisites

- [Umbrel](https://umbrel.com) running on a Raspberry Pi 4/5 or a PC
- The **Home Assistant** app installed and running on the same Umbrel (it is a required dependency)
- A Home Assistant long-lived access token (created inside Home Assistant)

## Installation

### 1. Add this community app store to Umbrel

Open your Umbrel dashboard, go to **App Store → ⋮ (menu) → Community App Stores**, and add:

```
https://github.com/mkeller0815/Umbrel-HA-MCP
```

### 2. Install the app

Find **Home Assistant MCP Server** in the app store and click **Install**. Umbrel will install the Home Assistant app first if it is not already running.

### 3. Create a Home Assistant access token

In Home Assistant, go to your **Profile → Long-Lived Access Tokens → Create Token**. Give it a name (e.g. "Umbrel MCP") and copy the token — you only see it once.

### 4. Configure the connection

Open the app from your Umbrel home screen. A setup page appears with the Home Assistant URL already pre-filled to `http://umbrel.local:8123`. Paste your token into the token field and click **Save**.

The status badge will turn green once the connection is verified.

### 5. Connect your AI client

Your MCP endpoint is:

```
http://umbrel.local:8086/mcp
```

Use this URL in your AI client of choice. Examples below.

## Connecting AI Clients

### Claude Desktop

Claude Desktop does not support HTTP MCP transports natively and requires a local stdio proxy. The easiest way is `mcp-remote` via `npx` (requires Node.js):

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "home-assistant": {
      "command": "npx",
      "args": ["mcp-remote", "http://umbrel.local:8086/mcp", "--allow-http"]
    }
  }
}
```

On macOS with Node.js installed via Homebrew, use the full path to `npx`:

```json
{
  "mcpServers": {
    "home-assistant": {
      "command": "/opt/homebrew/bin/npx",
      "args": ["mcp-remote", "http://umbrel.local:8086/mcp", "--allow-http"]
    }
  }
}
```

Restart Claude Desktop after saving. If new tools don't appear after enabling features, restart Claude Desktop again to refresh the tool list.

> **Note:** `--allow-http` is required because `mcp-remote` blocks non-HTTPS URLs by default. If you use the [Tailscale HTTPS endpoint](#remote-access-via-tailscale-https), omit `--allow-http` and use the `https://` URL instead.

### Claude Code

```bash
claude mcp add-json home-assistant '{
  "url": "http://umbrel.local:8086/mcp",
  "type": "http"
}'
```

### Other MCP clients

Any client that supports the streamable-HTTP MCP transport can connect directly to `http://umbrel.local:8086/mcp`. For clients that require stdio, use `mcp-remote` as shown in the Claude Desktop example above.

Replace `umbrel.local` with your Umbrel's IP address if the hostname does not resolve on your network.

## How it works

The app runs two containers:

| Container | Role |
|---|---|
| `ui` | Setup page at `/` + reverse proxy for `/mcp/*` |
| `server` | Ha-mcp in HTTP mode, internal port 8087 |

The setup UI writes your Home Assistant URL, token, and feature flags to `app-data/ha-mcp-server/data/.env`. Ha-mcp reads that file on startup. The MCP endpoint at `/mcp` is proxied transparently through the UI container, so clients always connect to port 8086.

```
Browser / AI client (local)
       │  http://umbrel.local:8086/mcp
       │
  Umbrel app_proxy :8086
       │
  setup-ui container :8086
  ├── GET /            → setup form (token, feature flags, Tailscale toggle)
  ├── POST /api/save   → writes .env
  └── /mcp/*           → ha-mcp container :8087

AI client (remote, optional)
       │  https://<tailnet-hostname>/mcp
       │
  Tailscale Serve (HTTPS, auto-cert)
       │
  localhost:8086  →  setup-ui container
```

## Remote access via Tailscale (HTTPS)

If the [Tailscale app](https://umbrel.com/umbrel-apps/tailscale) is installed on your Umbrel, you can enable a secure HTTPS endpoint reachable from anywhere on your tailnet — no port forwarding required.

### Setup

1. Install the **Tailscale** app on Umbrel and connect it to your tailnet
2. Open the HA MCP Server setup UI
3. Expand **Tailscale HTTPS access** and check **Enable Tailscale HTTPS endpoint**
4. Click **Save & Restart**, then stop and start the app in Umbrel

On the next start the `pre-start` hook automatically runs `tailscale serve` inside the Tailscale container, which proxies `https://<your-umbrel-hostname>.<tailnet>.ts.net` → `http://localhost:8086`. The setup UI will show the HTTPS MCP endpoint in purple once configured:

```
https://umbrel.<tailnet>.ts.net/mcp
```

Use this HTTPS URL in your AI client. With the Tailscale endpoint you can drop `--allow-http` from the `mcp-remote` args in Claude Desktop.

### Notes

- **No hard dependency**: if Tailscale is not installed the app works normally over HTTP on the local network
- **Opt-in**: Tailscale Serve is only configured when the toggle is enabled; disabling it removes the Serve config on next restart
- The Tailscale app uses host networking on Umbrel, so `tailscale serve` on port 8086 reaches the MCP server directly on `localhost`
- The HTTPS certificate is issued automatically by Tailscale via Let's Encrypt — no manual cert management needed

## Enabling beta features (YAML editing, filesystem tools, etc.)

Ha-mcp ships with several powerful but potentially dangerous tools disabled by default. You can enable them from the setup UI:

1. Open the app from your Umbrel home screen
2. Expand the **Beta features** section
3. Check **Enable beta features (master switch)** and any sub-features you want
4. Click **Save & Restart**
5. Stop and start the app in Umbrel so the server restarts with the new settings

The master switch must be on for any sub-feature to work. Available sub-features:

| Feature | What it does |
|---|---|
| YAML config editing | Lets the AI add, replace, or remove keys in `configuration.yaml` and `packages/*.yaml` |
| Filesystem tools | Gives the AI direct read/write access to your HA filesystem |
| Custom component integration | Lets the AI install and manage custom components |
| Code mode | Lets the AI execute sandboxed Python scripts in Home Assistant |

> **Warning:** These tools can permanently damage your Home Assistant installation. Take a backup before enabling them.

### Tools not showing up after enabling beta features

If you enable beta features but your AI client does not see the new tools (e.g. Claude says it cannot find `ha_config_set_yaml`), the client has a cached copy of the tool list from before the restart. **Restart your AI client** (Claude Desktop, etc.) to force it to re-fetch the tool catalog from the MCP server.

## Updating

When a new version of ha-mcp is released, update the image tag and digest in `ha-mcp-server/docker-compose.yml` and bump `version` in `ha-mcp-server/umbrel-app.yml`. Umbrel will offer the update to users.

When the setup-ui container changes, push to this repo and GitHub Actions rebuilds `ghcr.io/mkeller0815/ha-mcp-setup-ui` for both `linux/amd64` and `linux/arm64`. Update the digest in `docker-compose.yml` after the build completes.

## Repository structure

```
umbrel-app-store.yml          # Community app store manifest
ha-mcp-server/
  umbrel-app.yml              # Umbrel app manifest
  docker-compose.yml          # Service definitions
  hooks/pre-start             # Creates .env, sets permissions, configures Tailscale Serve
  data/.gitkeep               # Ensures persistence directory exists
setup-ui/
  server.py                   # Setup UI + proxy server (Python/aiohttp)
  Dockerfile                  # Builds ghcr.io/mkeller0815/ha-mcp-setup-ui
.github/workflows/
  build-setup-ui.yml          # Builds and publishes the setup-ui image on push
TODO.md                       # Planned features and improvements
```

## Credits

- [ha-mcp](https://github.com/homeassistant-ai/ha-mcp) by homeassistant-ai — the MCP server this package wraps
- [Umbrel](https://umbrel.com) — the personal server OS
- [FastMCP](https://github.com/jlowin/fastmcp) — the MCP framework ha-mcp is built on

## License

MIT
