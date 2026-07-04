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

## HTTPS without Tailscale

Explore options for users who don't have Tailscale but want HTTPS:
- Umbrel's built-in Tor/onion address (already available, but slow)
- Cloudflare Tunnel as an Umbrel app
- Self-signed cert with user-accepted CA

---

## Auto-update ha-mcp version

When ha-mcp releases a new version, currently requires manual update of the image tag and digest in `docker-compose.yml`. Could be automated with a GitHub Actions workflow that watches the upstream `ghcr.io/homeassistant-ai/ha-mcp` registry and opens a PR with the updated digest.
