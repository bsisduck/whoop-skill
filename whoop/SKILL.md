---
name: whoop
description: Build integrations with the WHOOP fitness/health API. Use when the user wants to fetch or analyze WHOOP data (workouts, sleep, recovery, strain, HRV, cycles), set up WHOOP OAuth2 authentication, create webhook handlers for WHOOP events, build dashboards or apps using WHOOP health metrics, or mentions WHOOP in any development context. Covers the full WHOOP Developer API v2.
---

# WHOOP API Integration

Build apps that read WHOOP health data: workouts, sleep, recovery, strain, cycles, and body measurements.

## Quick Start

### 1. Auth Setup

Register at [WHOOP Developer Dashboard](https://developer-dashboard.whoop.com). Max 5 apps per account.

Run the bundled auth helper:
```bash
python3 scripts/whoop_auth.py auth \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_SECRET \
  --redirect-uri https://yourapp.com/callback
```

User authorizes in browser, then exchange the code:
```bash
python3 scripts/whoop_auth.py exchange --code AUTH_CODE_FROM_REDIRECT
```

Tokens stored at `~/.whoop/tokens.json` (chmod 600). Auto-refresh with `offline` scope.

### 2. Fetch Data

```python
from whoop_client import WhoopClient

client = WhoopClient.from_stored_tokens()
profile = client.get_profile()
workouts = client.get_all_workouts(start="2024-01-01T00:00:00.000Z")
recovery = client.get_all_recoveries(start="2024-01-01T00:00:00.000Z")
```

CLI usage:
```bash
python3 scripts/whoop_client.py profile
python3 scripts/whoop_client.py workouts --start 2024-01-01 --all
python3 scripts/whoop_client.py recovery --start 2024-01-01
python3 scripts/whoop_client.py sleep --start 2024-01-01 --end 2024-02-01
python3 scripts/whoop_client.py cycles --limit 5
python3 scripts/whoop_client.py body
```

## OAuth2 Flow

Authorization Code flow with these endpoints:
- Auth: `https://api.prod.whoop.com/oauth/oauth2/auth`
- Token: `https://api.prod.whoop.com/oauth/oauth2/token`

Scopes: `read:profile`, `read:body_measurement`, `read:cycles`, `read:recovery`, `read:sleep`, `read:workout`, `offline`

Always include `offline` scope for refresh tokens. Tokens expire per `expires_in` field — refresh before expiry. New tokens invalidate old ones; use a background refresh job to avoid race conditions.

Client secret must **never** be exposed in frontend/mobile code.

## API Endpoints Summary

Base URL: `https://api.prod.whoop.com/developer`

| Method | Path | Scope | Paginated |
|--------|------|-------|-----------|
| GET | `/v2/user/profile/basic` | `read:profile` | No |
| GET | `/v2/user/measurement/body` | `read:body_measurement` | No |
| DELETE | `/v2/user/access` | — | No |
| GET | `/v2/cycle` | `read:cycles` | Yes |
| GET | `/v2/cycle/{cycleId}` | `read:cycles` | No |
| GET | `/v2/cycle/{cycleId}/sleep` | `read:sleep` | No |
| GET | `/v2/cycle/{cycleId}/recovery` | `read:recovery` | No |
| GET | `/v2/activity/sleep` | `read:sleep` | Yes |
| GET | `/v2/activity/sleep/{sleepId}` | `read:sleep` | No |
| GET | `/v2/recovery` | `read:recovery` | Yes |
| GET | `/v2/activity/workout` | `read:workout` | Yes |
| GET | `/v2/activity/workout/{workoutId}` | `read:workout` | No |
| GET | `/v1/activity-mapping/{v1Id}` | — | No |

Paginated endpoints accept: `limit` (max 25), `start`, `end` (ISO 8601), `nextToken`.

Rate limits: 100/min, 10K/day. Headers: `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

## WHOOP Domain Model

**Cycle**: One physiological day (sleep-to-sleep, not calendar day). Contains strain and links to sleep/recovery/workouts.

**Strain (0-21)**: Cardiovascular load on Borg Scale. Non-linear — 16→17 is harder than 4→5.
- Light: 0-9 | Moderate: 10-13 | High: 14-17 | All Out: 18-21

**Recovery (0-100%)**: Morning readiness from RHR, HRV, sleep, SpO2, skin temp.
- Green: 67-100% | Yellow: 34-66% | Red: 0-33%

**Sleep**: Tracks stages (light, SWS, REM), calculates need (baseline + debt + strain - naps), reports performance/consistency/efficiency percentages.

**HRV (RMSSD)**: Milliseconds. Higher = better parasympathetic recovery.

**Score states**: `SCORED` (data ready), `PENDING_SCORE` (processing), `UNSCORABLE` (insufficient data).

## Webhooks

Set up real-time notifications instead of polling. See [references/webhooks.md](references/webhooks.md) for:
- Signature verification (HMAC-SHA256) with Flask/Express examples
- All 6 event types (workout/sleep/recovery × updated/deleted)
- Retry policy (5 retries over ~1 hour)

Webhooks send notifications only — fetch full data via API using the UUID from the event payload.

## Bundled Scripts

- **`scripts/whoop_auth.py`**: OAuth2 token management (auth flow, exchange, refresh, status check). Stores tokens at `~/.whoop/tokens.json`.
- **`scripts/whoop_client.py`**: Full API client with auto-pagination, rate limit retry, and CLI interface. Import as library or run standalone.

## Full API Reference

See [references/api_reference.md](references/api_reference.md) for complete endpoint documentation with response schemas, data models, sport type IDs, and all field definitions.
