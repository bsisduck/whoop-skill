#!/usr/bin/env python3
"""WHOOP OAuth2 Authentication Helper.

Handles the full OAuth2 authorization code flow:
  1. Generate authorization URL for user consent
  2. Exchange authorization code for access/refresh tokens
  3. Refresh expired tokens automatically
  4. Store tokens securely in a JSON file

Usage:
  # Start auth flow (opens browser)
  python3 whoop_auth.py auth --client-id YOUR_ID --client-secret YOUR_SECRET --redirect-uri YOUR_URI

  # Exchange code after redirect
  python3 whoop_auth.py exchange --code AUTH_CODE

  # Refresh tokens
  python3 whoop_auth.py refresh

  # Show current token status
  python3 whoop_auth.py status
"""

import argparse
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
DEFAULT_TOKEN_FILE = Path.home() / ".whoop" / "tokens.json"
DEFAULT_CONFIG_FILE = Path.home() / ".whoop" / "config.json"
HTTP_TIMEOUT = 30

ALL_SCOPES = [
    "read:recovery",
    "read:cycles",
    "read:workout",
    "read:sleep",
    "read:profile",
    "read:body_measurement",
    "offline",
]


class WhoopAuthError(Exception):
    pass


def _ensure_dir(p):
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)


def load_config(path=None):
    p = Path(path) if path else DEFAULT_CONFIG_FILE
    if not p.exists():
        return {}
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise WhoopAuthError(f"Failed to read config {p}: {e}")


def save_config(config, path=None):
    p = Path(path) if path else DEFAULT_CONFIG_FILE
    _ensure_dir(p)
    with open(p, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(p, 0o600)


def load_tokens(path=None):
    p = Path(path) if path else DEFAULT_TOKEN_FILE
    if not p.exists():
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise WhoopAuthError(f"Failed to read tokens {p}: {e}")


def save_tokens(tokens, path=None):
    p = Path(path) if path else DEFAULT_TOKEN_FILE
    _ensure_dir(p)
    tokens["saved_at"] = int(time.time())
    with open(p, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(p, 0o600)


def generate_auth_url(client_id, redirect_uri, scopes=None, state=None):
    if scopes is None:
        scopes = ALL_SCOPES
    if state is None:
        state = secrets.token_urlsafe(32)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}", state


def exchange_code(client_id, client_secret, code, redirect_uri):
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "WHOOP-Skill/1.0")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise WhoopAuthError(f"Token exchange failed (HTTP {e.code}): {body}")
    except urllib.error.URLError as e:
        raise WhoopAuthError(f"Token exchange failed: {e.reason}")


def refresh_tokens(client_id, client_secret, refresh_token):
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "WHOOP-Skill/1.0")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise WhoopAuthError(f"Token refresh failed (HTTP {e.code}): {body}")
    except urllib.error.URLError as e:
        raise WhoopAuthError(f"Token refresh failed: {e.reason}")


def is_token_expired(tokens):
    if not tokens or "saved_at" not in tokens or "expires_in" not in tokens:
        return True
    return time.time() > (tokens["saved_at"] + tokens["expires_in"] - 60)


def get_valid_token(config_path=None, token_path=None):
    """Return a valid access token, refreshing if needed.

    Raises WhoopAuthError instead of calling sys.exit so callers can handle it.
    """
    config = load_config(config_path)
    tokens = load_tokens(token_path)
    if not tokens:
        raise WhoopAuthError("No tokens found. Run 'whoop_auth.py auth' first.")
    if is_token_expired(tokens):
        if "refresh_token" not in tokens:
            raise WhoopAuthError("Token expired and no refresh token. Re-authenticate.")
        old_refresh = tokens["refresh_token"]
        new_tokens = refresh_tokens(
            config["client_id"], config["client_secret"], old_refresh
        )
        if "refresh_token" not in new_tokens:
            new_tokens["refresh_token"] = old_refresh
        save_tokens(new_tokens, token_path)
        return new_tokens["access_token"]
    return tokens["access_token"]


def cmd_auth(args):
    config = {
        "client_id": args.client_id,
        "client_secret": args.client_secret,
        "redirect_uri": args.redirect_uri,
    }
    save_config(config)
    scopes = args.scopes.split(",") if args.scopes else ALL_SCOPES
    url, state = generate_auth_url(args.client_id, args.redirect_uri, scopes)
    config["state"] = state
    save_config(config)
    print(f"Open this URL in your browser:\n\n{url}\n")
    print(f"State token (for verification): {state}")
    print(f"\nAfter authorizing, run:\n  python3 {sys.argv[0]} exchange --code <AUTH_CODE>")


def cmd_exchange(args):
    config = load_config()
    if not config.get("client_id"):
        print("No config found. Run 'auth' command first.", file=sys.stderr)
        sys.exit(1)
    tokens = exchange_code(
        config["client_id"], config["client_secret"], args.code, config["redirect_uri"]
    )
    save_tokens(tokens)
    print("Tokens saved successfully.")
    print(f"  Access token expires in: {tokens.get('expires_in', '?')}s")
    print(f"  Refresh token: {'present' if 'refresh_token' in tokens else 'missing (add offline scope)'}")


def cmd_refresh(args):
    config = load_config()
    tokens = load_tokens()
    if not tokens or "refresh_token" not in tokens:
        print("No refresh token available.", file=sys.stderr)
        sys.exit(1)
    old_refresh = tokens["refresh_token"]
    new_tokens = refresh_tokens(config["client_id"], config["client_secret"], old_refresh)
    if "refresh_token" not in new_tokens:
        new_tokens["refresh_token"] = old_refresh
    save_tokens(new_tokens)
    print("Tokens refreshed successfully.")


def cmd_status(args):
    tokens = load_tokens()
    if not tokens:
        print("No tokens found.")
        return
    expired = is_token_expired(tokens)
    saved_at = tokens.get("saved_at", 0)
    expires_in = tokens.get("expires_in", 0)
    remaining = max(0, (saved_at + expires_in) - int(time.time()))
    print(f"Token status: {'EXPIRED' if expired else 'VALID'}")
    print(f"  Expires in: {remaining}s")
    print(f"  Has refresh token: {'yes' if 'refresh_token' in tokens else 'no'}")
    print(f"  Scopes: {tokens.get('scope', 'unknown')}")


def main():
    parser = argparse.ArgumentParser(description="WHOOP OAuth2 Authentication")
    sub = parser.add_subparsers(dest="command", required=True)

    auth_p = sub.add_parser("auth", help="Start OAuth2 authorization flow")
    auth_p.add_argument("--client-id", required=True)
    auth_p.add_argument("--client-secret", required=True)
    auth_p.add_argument("--redirect-uri", required=True)
    auth_p.add_argument("--scopes", help="Comma-separated scopes (default: all)")
    auth_p.set_defaults(func=cmd_auth)

    exc_p = sub.add_parser("exchange", help="Exchange authorization code for tokens")
    exc_p.add_argument("--code", required=True)
    exc_p.set_defaults(func=cmd_exchange)

    ref_p = sub.add_parser("refresh", help="Refresh access token")
    ref_p.set_defaults(func=cmd_refresh)

    stat_p = sub.add_parser("status", help="Show token status")
    stat_p.set_defaults(func=cmd_status)

    args = parser.parse_args()
    try:
        args.func(args)
    except WhoopAuthError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
