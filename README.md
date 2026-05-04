# whoop-skill

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill for the [WHOOP API v2](https://developer.whoop.com). Also works standalone as a Python CLI/library — no Claude Code required.

## Features

- **Full API coverage** — All v2 endpoints: workouts, sleep, recovery, cycles, body measurements, user profile
- **OAuth2 authentication** — Authorization code flow with automatic token refresh and secure storage
- **Auto-pagination** — Transparently iterate through all pages of collection endpoints
- **Rate limit handling** — Automatic retry on 429 with backoff (100 req/min, 10K req/day)
- **Webhooks v2** — Event handling with HMAC-SHA256 signature verification (Flask + Express examples)
- **Domain knowledge** — Strain (0-21), Recovery (0-100%), Sleep stages, HRV, heart rate zones
- **CLI + Library** — Use the bundled client from the command line or import it in your code

## Setup

### Step 1: Create a WHOOP developer app

1. Go to [developer-dashboard.whoop.com](https://developer-dashboard.whoop.com)
2. Sign in with your WHOOP account
3. Click **Create App**
4. Select all scopes you need (tip: select all + `offline` for refresh tokens)
5. Under **Redirect URLs**, add: `http://localhost:8080/callback`
6. Click **Create**
7. Copy your **Client ID** and **Client Secret**

### Step 2: Authenticate

```bash
# Start the auth flow
python3 whoop/scripts/whoop_auth.py auth \
  --client-id YOUR_CLIENT_ID \
  --client-secret YOUR_CLIENT_SECRET \
  --redirect-uri http://localhost:8080/callback
```

This prints a URL. Open it in your browser, log in, and click **Authorize**.

Your browser will redirect to a page that won't load (that's expected). Look at the URL bar — it will look like:

```
http://localhost:8080/callback?code=abc123xyz...&state=...
```

Copy the `code` value and run:

```bash
python3 whoop/scripts/whoop_auth.py exchange --code PASTE_CODE_HERE
```

You should see `Tokens saved successfully.`

### Step 3: Verify it works

```bash
python3 whoop/scripts/whoop_client.py profile
```

This should print your name and email. You're all set.

### Step 4 (optional): Install as Claude Code skill

```bash
claude skill add /path/to/whoop-skill/whoop
```

Now Claude automatically knows the WHOOP API whenever you mention it.

## Quick examples

```bash
# Recent workouts
python3 whoop/scripts/whoop_client.py workouts --start 2024-01-01

# All sleep data (auto-paginates)
python3 whoop/scripts/whoop_client.py sleep --start 2024-01-01 --all

# Recovery scores
python3 whoop/scripts/whoop_client.py recovery --start 2024-01-01

# Body measurements
python3 whoop/scripts/whoop_client.py body

# Token status
python3 whoop_auth.py status
```

Or as a Python library:

```python
from whoop_client import WhoopClient

client = WhoopClient.from_stored_tokens()
workouts = client.get_all_workouts(start="2024-01-01T00:00:00.000Z")
```

## What's inside

```
whoop/
├── SKILL.md                 # Skill definition for Claude Code
├── scripts/
│   ├── whoop_auth.py        # OAuth2 auth (login, token refresh)
│   └── whoop_client.py      # API client (all endpoints, pagination, rate limits)
└── references/
    ├── api_reference.md     # Full endpoint docs, schemas, 100+ sport types
    └── webhooks.md          # Webhook v2 setup with Flask + Express examples
```

## Requirements

- Python 3.8+
- A WHOOP membership

## License

MIT
