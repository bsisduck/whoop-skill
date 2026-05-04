#!/usr/bin/env python3
"""WHOOP API Client.

Full-featured client for the WHOOP Developer API v2.
Handles authentication, pagination, rate limiting, and all endpoints.

Usage as library:
  from whoop_client import WhoopClient
  client = WhoopClient(access_token="...")

  # Or with auto-token management (requires whoop_auth on sys.path):
  client = WhoopClient.from_stored_tokens()

  profile = client.get_profile()
  workouts = client.get_all_workouts(start="2024-01-01T00:00:00.000Z")
  recovery = client.get_all_recoveries(start="2024-01-01T00:00:00.000Z")

Usage as CLI:
  python3 whoop_client.py profile
  python3 whoop_client.py workouts --start 2024-01-01 --end 2024-02-01
  python3 whoop_client.py cycles --limit 5
  python3 whoop_client.py sleep --start 2024-01-01
  python3 whoop_client.py recovery --start 2024-01-01
  python3 whoop_client.py body
  python3 whoop_client.py get cycle 12345
  python3 whoop_client.py get workout 550e8400-...
  python3 whoop_client.py revoke
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://api.prod.whoop.com/developer"
HTTP_TIMEOUT = 30
MAX_PAGINATION_PAGES = 500


class RateLimitError(Exception):
    def __init__(self, retry_after=None):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s" if retry_after else "Rate limited")


class WhoopAPIError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class WhoopClient:
    def __init__(self, access_token, base_url=BASE_URL):
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    @classmethod
    def from_stored_tokens(cls, config_path=None, token_path=None):
        scripts_dir = str(Path(__file__).resolve().parent)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from whoop_auth import get_valid_token
        token = get_valid_token(config_path, token_path)
        return cls(access_token=token)

    def _request(self, method, path, params=None):
        url = f"{self.base_url}{path}"
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                url = f"{url}?{urllib.parse.urlencode(filtered)}"

        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {self.access_token}")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "WHOOP-Skill/1.0")

        try:
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                self.rate_limit_remaining = resp.headers.get("X-RateLimit-Remaining")
                self.rate_limit_reset = resp.headers.get("X-RateLimit-Reset")
                if resp.status == 204:
                    return None
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                retry_after = e.headers.get("X-RateLimit-Reset")
                raise RateLimitError(retry_after)
            body = e.read().decode() if e.fp else str(e)
            raise WhoopAPIError(e.code, body)

    def _request_with_retry(self, method, path, params=None, max_retries=2):
        for attempt in range(max_retries + 1):
            try:
                return self._request(method, path, params)
            except RateLimitError as e:
                if attempt == max_retries:
                    raise
                try:
                    wait = int(e.retry_after) if e.retry_after else 5
                except (ValueError, TypeError):
                    wait = 5
                wait = min(wait, 60)
                time.sleep(wait)

    def _paginate(self, path, start=None, end=None, limit=None):
        params = {"start": start, "end": end, "limit": limit, "nextToken": None}
        all_records = []
        for _ in range(MAX_PAGINATION_PAGES):
            data = self._request_with_retry("GET", path, params)
            if not data or not isinstance(data, dict):
                break
            records = data.get("records", [])
            all_records.extend(records)
            next_token = data.get("next_token")
            if not next_token or not records:
                break
            params["nextToken"] = next_token
        return all_records

    # --- User ---

    def get_profile(self):
        return self._request_with_retry("GET", "/v2/user/profile/basic")

    def get_body_measurement(self):
        return self._request_with_retry("GET", "/v2/user/measurement/body")

    def revoke_access(self):
        return self._request_with_retry("DELETE", "/v2/user/access")

    # --- Cycles ---

    def get_cycle(self, cycle_id):
        return self._request_with_retry("GET", f"/v2/cycle/{cycle_id}")

    def get_cycles(self, start=None, end=None, limit=None):
        return self._request_with_retry("GET", "/v2/cycle", {
            "start": start, "end": end, "limit": limit,
        })

    def get_all_cycles(self, start=None, end=None, limit=25):
        return self._paginate("/v2/cycle", start, end, limit)

    def get_cycle_sleep(self, cycle_id):
        return self._request_with_retry("GET", f"/v2/cycle/{cycle_id}/sleep")

    def get_cycle_recovery(self, cycle_id):
        return self._request_with_retry("GET", f"/v2/cycle/{cycle_id}/recovery")

    # --- Sleep ---

    def get_sleep(self, sleep_id):
        return self._request_with_retry("GET", f"/v2/activity/sleep/{sleep_id}")

    def get_sleeps(self, start=None, end=None, limit=None):
        return self._request_with_retry("GET", "/v2/activity/sleep", {
            "start": start, "end": end, "limit": limit,
        })

    def get_all_sleeps(self, start=None, end=None, limit=25):
        return self._paginate("/v2/activity/sleep", start, end, limit)

    # --- Recovery ---

    def get_recoveries(self, start=None, end=None, limit=None):
        return self._request_with_retry("GET", "/v2/recovery", {
            "start": start, "end": end, "limit": limit,
        })

    def get_all_recoveries(self, start=None, end=None, limit=25):
        return self._paginate("/v2/recovery", start, end, limit)

    # --- Workouts ---

    def get_workout(self, workout_id):
        return self._request_with_retry("GET", f"/v2/activity/workout/{workout_id}")

    def get_workouts(self, start=None, end=None, limit=None):
        return self._request_with_retry("GET", "/v2/activity/workout", {
            "start": start, "end": end, "limit": limit,
        })

    def get_all_workouts(self, start=None, end=None, limit=25):
        return self._paginate("/v2/activity/workout", start, end, limit)

    # --- Activity Mapping (v1 → v2) ---

    def map_v1_activity(self, v1_id):
        return self._request_with_retry("GET", f"/v1/activity-mapping/{v1_id}")


def _parse_date(s):
    if not s:
        return None
    if "T" in s:
        return s
    return f"{s}T00:00:00.000Z"


def main():
    parser = argparse.ArgumentParser(description="WHOOP API Client CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ["cycles", "sleep", "recovery", "workouts"]:
        p = sub.add_parser(name, help=f"List {name}")
        p.add_argument("--start", help="Start date (YYYY-MM-DD or ISO)")
        p.add_argument("--end", help="End date (YYYY-MM-DD or ISO)")
        p.add_argument("--limit", type=int, default=25)
        p.add_argument("--all", action="store_true", help="Paginate through all results")

    sub.add_parser("profile", help="Get user profile")
    sub.add_parser("body", help="Get body measurements")
    sub.add_parser("revoke", help="Revoke OAuth access")

    get_p = sub.add_parser("get", help="Get single resource by ID")
    get_p.add_argument("type", choices=["cycle", "sleep", "workout", "cycle-sleep", "cycle-recovery"])
    get_p.add_argument("id", help="Resource ID")

    map_p = sub.add_parser("map", help="Map v1 activity ID to v2 UUID")
    map_p.add_argument("v1_id", help="Legacy v1 activity ID (integer)")

    args = parser.parse_args()
    client = WhoopClient.from_stored_tokens()

    result = None
    if args.command == "profile":
        result = client.get_profile()
    elif args.command == "body":
        result = client.get_body_measurement()
    elif args.command == "revoke":
        client.revoke_access()
        print("OAuth access revoked.")
        return
    elif args.command == "map":
        result = client.map_v1_activity(args.v1_id)
    elif args.command == "get":
        fn = {
            "cycle": client.get_cycle,
            "sleep": client.get_sleep,
            "workout": client.get_workout,
            "cycle-sleep": client.get_cycle_sleep,
            "cycle-recovery": client.get_cycle_recovery,
        }
        result = fn[args.type](args.id)
    elif args.command in ("cycles", "sleep", "recovery", "workouts"):
        start = _parse_date(args.start)
        end = _parse_date(args.end)
        fn_map = {
            "cycles": (client.get_all_cycles, client.get_cycles),
            "sleep": (client.get_all_sleeps, client.get_sleeps),
            "recovery": (client.get_all_recoveries, client.get_recoveries),
            "workouts": (client.get_all_workouts, client.get_workouts),
        }
        all_fn, page_fn = fn_map[args.command]
        result = all_fn(start, end, args.limit) if args.all else page_fn(start, end, args.limit)

    if result is not None:
        json.dump(result, sys.stdout, indent=2, default=str)
        print()


if __name__ == "__main__":
    main()
