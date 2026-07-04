"""
Setup UI for ha-mcp on Umbrel.
Serves the token configuration page at / and proxies /mcp/* to ha-mcp.
"""

import asyncio
import os
import re
from pathlib import Path

import aiohttp
from aiohttp import web

ENV_FILE = Path(os.environ.get("HA_MCP_ENV_FILE", "/data/.env"))
HA_MCP_URL = os.environ.get("HA_MCP_INTERNAL_URL", "http://localhost:8087")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "8086"))
UI_VERSION = os.environ.get("UI_VERSION", "dev")
HA_MCP_VERSION = os.environ.get("HA_MCP_VERSION", "")
APP_VERSION = os.environ.get("APP_VERSION", "")

# Feature flags exposed in the UI. Each entry: (env_var, label, warning)
FEATURE_FLAGS = [
    (
        "ENABLE_BETA_FEATURES",
        "Enable beta features (master switch)",
        "⚠ These tools can permanently damage your Home Assistant. Take a backup first.",
    ),
    (
        "ENABLE_YAML_CONFIG_EDITING",
        "Enable YAML config editing",
        "Allows AI to edit configuration.yaml and packages/*.yaml.",
    ),
    (
        "ENABLE_FILESYSTEM_TOOLS",
        "Enable filesystem tools",
        "Gives the AI direct read/write access to your HA filesystem.",
    ),
    (
        "ENABLE_CUSTOM_COMPONENT_INTEGRATION",
        "Enable custom component integration",
        "Allows AI to install and manage custom components (HACS etc.).",
    ),
    (
        "ENABLE_CODE_MODE",
        "Enable code mode",
        "Allows AI to execute sandboxed Python scripts in Home Assistant.",
    ),
]


def _read_env() -> dict[str, str]:
    result = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                result[k.strip()] = v.strip()
    return result


def _write_env(values: dict[str, str]) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = _read_env()
    current.update(values)
    lines = []
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                if k in current:
                    lines.append(f"{k}={current.pop(k)}")
                else:
                    lines.append(line)
            else:
                lines.append(line)
    for k, v in current.items():
        lines.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(lines) + "\n")


async def _check_ha_connection(url: str, token: str) -> tuple[bool, str]:
    if not token:
        return False, "No token configured"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{url}/api/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=5),
                ssl=False,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return True, data.get("message", "Connected")
                return False, f"HTTP {resp.status}"
    except aiohttp.ClientConnectorError:
        return False, "Cannot reach Home Assistant"
    except asyncio.TimeoutError:
        return False, "Connection timed out"
    except Exception as e:
        return False, str(e)


async def handle_index(request: web.Request) -> web.Response:
    env = _read_env()
    ha_url = env.get("HOMEASSISTANT_URL", "")
    token = env.get("HOMEASSISTANT_TOKEN", "")
    token_set = bool(token)

    tailscale_host = env.get("TAILSCALE_HOSTNAME", "")
    tailscale_enabled = env.get("TAILSCALE_SERVE_ENABLED", "").lower() == "true"
    connected, status_msg = await _check_ha_connection(ha_url, token)

    status_color = "#22c55e" if connected else ("#f59e0b" if token_set else "#ef4444")
    status_icon = "✓" if connected else ("⚠" if token_set else "✗")
    mcp_url = request.url.origin().with_path("/mcp")
    tailscale_mcp_url = f"https://{tailscale_host}/mcp" if (tailscale_host and tailscale_enabled) else ""

    # Build the connected-state block (endpoint boxes + settings link)
    if connected:
        tailscale_box = ""
        if tailscale_mcp_url:
            tailscale_box = f"""
    <div class="mcp-box" style="margin-top:.75rem;border-color:#6366f144;">
      <p style="color:#818cf8;">MCP endpoint — Tailscale (HTTPS, remote access)</p>
      <code style="color:#a5b4fc;">{tailscale_mcp_url}</code>
    </div>"""
        connected_block = f"""
    <hr class="divider">
    <div class="mcp-box">
      <p>MCP endpoint — local network</p>
      <code>{mcp_url}</code>
    </div>{tailscale_box}
    <a href="/mcp/settings" style="
      display:block; margin-top:1rem; padding:.6rem 1rem;
      background:#1e3a5f; border:1px solid #334155; border-radius:.5rem;
      color:#7dd3fc; font-size:.85rem; text-decoration:none; text-align:center;
    ">⚙ MCP Server Settings</a>"""
    else:
        connected_block = ""

    # Build feature flag checkboxes
    flag_rows = ""
    for env_var, label, warning in FEATURE_FLAGS:
        checked = "checked" if env.get(env_var, "").lower() == "true" else ""
        is_master = env_var == "ENABLE_BETA_FEATURES"
        indent = "" if is_master else "margin-left:1.25rem;"
        flag_rows += f"""
        <div class="flag-row" style="{indent}">
          <label class="flag-label">
            <input type="checkbox" name="{env_var}" value="true" {checked}>
            <span>{label}</span>
          </label>
          <div class="flag-warn">{warning}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Home Assistant MCP Server</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f172a; color: #e2e8f0; min-height: 100vh;
      display: flex; align-items: center; justify-content: center; padding: 1.5rem;
    }}
    .card {{
      background: #1e293b; border-radius: 1rem; padding: 2rem;
      width: 100%; max-width: 520px; box-shadow: 0 25px 50px rgba(0,0,0,.5);
    }}
    .logo {{ display: flex; align-items: center; gap: .75rem; margin-bottom: 1.75rem; }}
    .logo img {{ width: 40px; height: 40px; border-radius: .5rem; }}
    .logo h1 {{ font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }}
    .status-badge {{
      display: inline-flex; align-items: center; gap: .4rem;
      padding: .3rem .75rem; border-radius: 9999px; font-size: .8rem; font-weight: 600;
      background: {status_color}22; color: {status_color}; border: 1px solid {status_color}44;
      margin-bottom: 1.5rem;
    }}
    label {{ display: block; font-size: .85rem; color: #94a3b8; margin-bottom: .4rem; }}
    input[type="text"], input[type="password"] {{
      width: 100%; padding: .6rem .85rem; border-radius: .5rem;
      border: 1px solid #334155; background: #0f172a; color: #f1f5f9;
      font-size: .9rem; outline: none; transition: border-color .15s;
    }}
    input:focus {{ border-color: #3b82f6; }}
    .field {{ margin-bottom: 1rem; }}
    button[type="submit"] {{
      width: 100%; padding: .7rem; border-radius: .5rem; border: none;
      background: #3b82f6; color: #fff; font-size: .95rem; font-weight: 600;
      cursor: pointer; transition: background .15s; margin-top: .5rem;
    }}
    button[type="submit"]:hover {{ background: #2563eb; }}
    .mcp-box {{
      margin-top: 1.5rem; padding: 1rem; background: #0f172a;
      border-radius: .5rem; border: 1px solid #334155;
    }}
    .mcp-box p {{ font-size: .8rem; color: #64748b; margin-bottom: .4rem; }}
    .mcp-box code {{ font-size: .85rem; color: #7dd3fc; word-break: break-all; }}
    .msg {{ margin-top: .75rem; font-size: .85rem; padding: .5rem .75rem;
      border-radius: .4rem; }}
    .msg.ok {{ background: #16a34a22; color: #4ade80; }}
    .msg.err {{ background: #dc262622; color: #f87171; }}
    .divider {{ border: none; border-top: 1px solid #1e3a5f; margin: 1.25rem 0; }}
    details {{ margin-top: 1.25rem; }}
    summary {{
      cursor: pointer; font-size: .85rem; color: #94a3b8; padding: .5rem 0;
      user-select: none; list-style: none; display: flex; align-items: center; gap: .4rem;
    }}
    summary::before {{ content: "▶"; font-size: .7rem; transition: transform .15s; }}
    details[open] summary::before {{ transform: rotate(90deg); }}
    .flag-row {{ margin: .6rem 0; }}
    .flag-label {{
      display: flex; align-items: flex-start; gap: .5rem;
      font-size: .85rem; color: #cbd5e1; cursor: pointer; margin-bottom: .2rem;
    }}
    .flag-label input {{ margin-top: .15rem; flex-shrink: 0; }}
    .flag-warn {{ font-size: .75rem; color: #f59e0b; margin-left: 1.35rem; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">
      <img src="https://raw.githubusercontent.com/mkeller0815/Umbrel-HA-MCP/main/ha-mcp-server/icon.png" alt="">
      <h1>Home Assistant MCP Server</h1>
    </div>

    <div class="status-badge">{status_icon} {status_msg}</div>

    <form method="POST" action="/api/save">
      <div class="field">
        <label for="ha_url">Home Assistant URL</label>
        <input type="text" id="ha_url" name="ha_url"
          value="{ha_url}" placeholder="http://umbrel.local:8123">
      </div>
      <div class="field">
        <label for="token">Long-Lived Access Token</label>
        <input type="password" id="token" name="token"
          value="{token}" placeholder="Paste your token here"
          autocomplete="off">
        <small style="color:#64748b;font-size:.78rem;margin-top:.3rem;display:block">
          Get one from: Home Assistant → Profile → Long-Lived Access Tokens → Create Token
        </small>
      </div>

      <details>
        <summary>Tailscale HTTPS access</summary>
        <div class="flag-row" style="margin-top:.5rem;">
          <label class="flag-label">
            <input type="checkbox" name="TAILSCALE_SERVE_ENABLED" value="true" {"checked" if tailscale_enabled else ""}>
            <span>Enable Tailscale HTTPS endpoint</span>
          </label>
          <div class="flag-warn" style="color:#818cf8;">
            Requires the Tailscale app installed on Umbrel. Configures
            <code style="font-size:.75rem;">tailscale serve</code> on app restart so the MCP
            endpoint is reachable over HTTPS from anywhere on your tailnet.
          </div>
        </div>
        <p style="font-size:.75rem;color:#64748b;margin-top:.75rem;">
          Changes take effect after the app is stopped and started.
        </p>
      </details>

      <details>
        <summary>Beta features</summary>
        {flag_rows}
        <p style="font-size:.75rem;color:#64748b;margin-top:.75rem;">
          Changes take effect after the server restarts (stop &amp; start the app).
        </p>
      </details>

      <button type="submit">Save &amp; Restart</button>
    </form>

    {connected_block}

    <div style="margin-top:1.5rem;text-align:center;font-size:.8rem;color:#64748b;">
      {"App v" + APP_VERSION + "&nbsp;·&nbsp;" if APP_VERSION else ""}ha-mcp {HA_MCP_VERSION or "unknown"}&nbsp;·&nbsp;setup-ui {UI_VERSION}
    </div>
  </div>
</body>
</html>"""

    return web.Response(text=html, content_type="text/html")


async def handle_save(request: web.Request) -> web.Response:
    data = await request.post()
    ha_url = str(data.get("ha_url", "")).strip().rstrip("/")
    token = str(data.get("token", "")).strip()

    if not ha_url:
        raise web.HTTPBadRequest(text="ha_url is required")

    values: dict[str, str] = {
        "HOMEASSISTANT_URL": ha_url,
        "HOMEASSISTANT_TOKEN": token,
        "TAILSCALE_SERVE_ENABLED": "true" if data.get("TAILSCALE_SERVE_ENABLED") == "true" else "false",
    }

    # Write feature flags — unchecked boxes send nothing, so default to false
    for env_var, _, _ in FEATURE_FLAGS:
        values[env_var] = "true" if data.get(env_var) == "true" else "false"

    _write_env(values)

    raise web.HTTPSeeOther(location="/")


_HOP_BY_HOP = frozenset(
    ["transfer-encoding", "content-encoding", "connection",
     "keep-alive", "proxy-authenticate", "proxy-authorization",
     "te", "trailers", "upgrade"]
)

_SESSION: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _SESSION
    if _SESSION is None or _SESSION.closed:
        _SESSION = aiohttp.ClientSession()
    return _SESSION


async def handle_proxy(request: web.Request) -> web.Response | web.StreamResponse:
    """Proxy /mcp/* to ha-mcp. Streams SSE/chunked responses, buffers the rest."""
    path = request.match_info["path"]
    target = f"{HA_MCP_URL}/mcp{path}"
    if request.query_string:
        target += f"?{request.query_string}"

    req_headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in _HOP_BY_HOP and k.lower() != "host"}
    body = await request.read()

    session = await _get_session()
    try:
        resp = await session.request(
            request.method, target,
            headers=req_headers, data=body or None,
            timeout=aiohttp.ClientTimeout(connect=5, total=None),
            allow_redirects=False,
        )
    except aiohttp.ClientConnectorError as e:
        return web.Response(status=502, text=f"Cannot reach ha-mcp: {e}")
    except asyncio.TimeoutError:
        return web.Response(status=504, text="ha-mcp connection timed out")

    resp_headers = {k: v for k, v in resp.headers.items()
                    if k.lower() not in _HOP_BY_HOP}

    content_type = resp.headers.get("content-type", "")
    is_streaming = "text/event-stream" in content_type or resp.headers.get("transfer-encoding") == "chunked"

    if is_streaming:
        stream_resp = web.StreamResponse(status=resp.status, headers=resp_headers)
        await stream_resp.prepare(request)
        try:
            async for chunk in resp.content.iter_any():
                await stream_resp.write(chunk)
        except (ConnectionResetError, asyncio.CancelledError):
            pass
        finally:
            resp.close()
        return stream_resp
    else:
        body = await resp.read()
        resp.close()
        return web.Response(status=resp.status, headers=resp_headers, body=body)


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/save", handle_save)
    app.router.add_route("*", "/mcp{path:.*}", handle_proxy)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=LISTEN_PORT, access_log=None)
