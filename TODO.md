# TODO / Planned Features

## Dev/Beta/Production split

Set up a proper multi-tier deployment to allow development and testing without affecting user installations.

**Proposed setup:**

| Tier | Repo | Store URL | Docker image tag |
|---|---|---|---|
| Production | `Umbrel-HA-MCP` `main` | `github.com/mkeller0815/Umbrel-HA-MCP` | `:latest` |
| Dev/Beta | `Umbrel-HA-MCP-dev` `main` | `github.com/mkeller0815/Umbrel-HA-MCP-dev` | `:dev` |

**Steps needed:**
- Create a `dev` branch in this repo for development work
- Create a separate `Umbrel-HA-MCP-dev` GitHub repo that tracks the `dev` branch
- Add a GitHub Actions workflow that publishes `:dev` image tags from the `dev` branch
- Use a different app ID in the dev store (e.g. `ha-mcp-server-dev`) so both can be installed simultaneously on the same Umbrel
- Document the branching and release workflow

---

## Remote access options (needs testing)

Several options exist for accessing the MCP endpoint remotely. Each needs to be tested and documented properly before recommending to users.

### Tailscale ✅
Already implemented. Opt-in toggle in the setup UI. Auto-configures `tailscale serve` for HTTPS via Let's Encrypt. Fast and easy. **Recommended option.**

**Known prerequisite:** HTTPS certificates must be enabled for the Umbrel machine in the Tailscale admin console before `tailscale serve` works. The pre-start hook currently fails silently if this is not set up. A future improvement would be to detect the failure and write a warning to `.env` so the setup UI can display an actionable error message instead of just not showing the endpoint.

### WireGuard (needs testing)
Umbrel ships a WireGuard app. Once connected to the WireGuard VPN, the MCP endpoint is reachable at `http://<wireguard-ip>:8086/mcp`. Traffic is encrypted by the VPN tunnel even though the URL is HTTP.
- Test: install WireGuard app on Umbrel, connect a client, verify MCP reachability
- No additional app changes needed — just document the WireGuard IP as an alternative URL
- Add a note in the setup UI if WireGuard is detected (similar to Tailscale)

### Cloudflare Tunnel (needs testing)
Free, no open ports required, HTTPS via Cloudflare's CA. Requires a Cloudflare account and either the `cloudflared` Umbrel community app or manual setup.
- Test: set up a tunnel pointing to `localhost:8086`, verify MCP works through it
- Consider adding an opt-in toggle in the setup UI similar to Tailscale

### Tor / Onion address (not recommended for MCP)
Umbrel automatically creates a `.onion` hidden service for every app. Traffic is encrypted end-to-end by Tor without needing TLS certificates. However:
- The MCP client machine needs Tor installed and configured as a SOCKS5 proxy
- `mcp-remote` would need to route through `127.0.0.1:9050`
- Tor adds significant latency — bad for MCP which makes many rapid round-trips
- Complex client-side setup, not suitable for non-technical users
- **Verdict: dead end for MCP access, not worth pursuing**

---

## Self-signed HTTPS in the setup-ui container

Add native HTTPS support to the aiohttp server so users don't need Tailscale or WireGuard for an encrypted connection.

**Approach:**
- On first start, generate a self-signed certificate + private key and store them in `data/` (persists across restarts)
- Certificate SANs should cover `umbrel.local`, the Tailscale hostname (if known), and the LAN IP
- aiohttp supports TLS natively via `ssl.SSLContext` passed to `web.run_app()`
- Add `cryptography` package to the Dockerfile for cert generation
- User trusts the cert once in their browser; MCP clients like `mcp-remote` can skip validation or be passed the cert

**Open questions before implementing:**
- Replace HTTP entirely on port 8086, or run HTTPS on a second port (e.g. 8443) alongside HTTP for backwards compatibility?
- Should the setup UI offer a cert download so users can install the CA on their devices?

---

## Auto-update ha-mcp version

When ha-mcp releases a new version, currently requires manual update of the image tag and digest in `docker-compose.yml`. Could be automated with a GitHub Actions workflow that watches the upstream `ghcr.io/homeassistant-ai/ha-mcp` registry and opens a PR with the updated digest.
