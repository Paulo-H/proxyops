"""End-to-end smoke test for the ProxyOps API.

Exercises every router and simulates a scraping robot consuming the rotation
endpoints so the dashboard has real data afterwards.

Usage:
    python scripts/test_e2e.py
    BASE_URL=http://localhost:8000 ADMIN_EMAIL=... ADMIN_PASSWORD=... python scripts/test_e2e.py
    python scripts/test_e2e.py --keep      # do not delete the entities at the end
    python scripts/test_e2e.py --robot 50  # number of simulated robot iterations

Requires only the `requests` library (pip install requests).
"""

from __future__ import annotations

import argparse
import os
import random
import secrets
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import requests

# Windows consoles default to cp1252 and choke on the box-drawing/check
# characters we use for output. Force UTF-8 on Python 3.7+.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
API = f"{BASE_URL}/api/v1"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@proxyops.io")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme")

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"


# ---------- helpers ------------------------------------------------------------


@dataclass
class State:
    access_token: str = ""
    robot_api_key: str = ""
    created: dict[str, list[int]] = field(default_factory=dict)
    passed: int = 0
    failed: int = 0


def remember(state: State, kind: str, item_id: int) -> None:
    state.created.setdefault(kind, []).append(item_id)


def step(title: str) -> None:
    print(f"\n{CYAN}── {title} ──{RESET}")


def ok(msg: str, state: State) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")
    state.passed += 1


def fail(msg: str, state: State, detail: Any = None) -> None:
    print(f"  {RED}✗ {msg}{RESET}")
    if detail is not None:
        print(f"    {DIM}{detail}{RESET}")
    state.failed += 1


def headers(state: State) -> dict[str, str]:
    return {"Authorization": f"Bearer {state.access_token}"}


def call(method: str, path: str, *, state: State, expect: int | tuple[int, ...] = 200, **kwargs) -> Any:
    """HTTP call with built-in assertion. Raises on unexpected status."""
    url = f"{API}{path}"
    if "headers" not in kwargs:
        kwargs["headers"] = headers(state)
    elif state.access_token:
        kwargs["headers"].setdefault("Authorization", f"Bearer {state.access_token}")
    r = requests.request(method, url, timeout=20, **kwargs)
    expected = (expect,) if isinstance(expect, int) else expect
    if r.status_code not in expected:
        raise AssertionError(
            f"{method} {path} expected {expected} got {r.status_code}: {r.text[:300]}"
        )
    if r.status_code == 204 or not r.content:
        return None
    return r.json()


# ---------- test phases --------------------------------------------------------


def phase_auth(state: State) -> None:
    step("Auth")
    try:
        data = requests.post(
            f"{API}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10,
        ).json()
        state.access_token = data["access_token"]
        ok("login", state)
    except Exception as exc:
        fail("login", state, exc)
        sys.exit(1)

    me = call("GET", "/auth/me", state=state)
    assert me["email"] == ADMIN_EMAIL
    assert me["role"] == "admin", f"seeded user must be admin, got {me['role']}"
    ok(f"GET /auth/me → {me['email']} ({me['role']})", state)


def phase_provider(state: State) -> int:
    step("Providers")
    name = f"e2e-provider-{secrets.token_hex(3)}"
    provider = call("POST", "/providers", state=state, expect=201, json={
        "name": name,
        "website": "https://example.com",
        "contact_email": "billing@example.com",
        "notes": "Created by test_e2e.py",
    })
    remember(state, "providers", provider["id"])
    ok(f"created provider #{provider['id']} ({name})", state)

    providers = call("GET", "/providers", state=state)
    assert any(p["id"] == provider["id"] for p in providers)
    ok(f"listed providers ({len(providers)} total)", state)

    updated = call("PATCH", f"/providers/{provider['id']}", state=state, json={"notes": "updated"})
    assert updated["notes"] == "updated"
    ok("patched provider notes", state)
    return provider["id"]


def phase_strategy(state: State) -> dict[str, int]:
    """Create one preset per algorithm so the comparison view has data.

    Returns a dict {kind: strategy_id}.
    """
    step("Strategy presets")
    kinds = call("GET", "/strategies/kinds", state=state)
    bayes = next(k for k in kinds if k["kind"] == "bayesian_beta")
    ok(f"introspected {len(kinds)} strategy kinds (bayesian_beta has {len(bayes['parameters'])} params)", state)

    tag = secrets.token_hex(3)
    presets = {
        "round_robin": {"max_logs_per_proxy": 10},
        "random": {},
        "bayesian_beta": {
            "decay_rate_success": 0.001,
            "decay_rate_error": 0.0003,
            "initial_alpha": 5.0,
            "initial_beta": 1.0,
            "max_logs_per_proxy": 100,
        },
        "exponential_backoff": {
            "base_backoff_minutes": 0.1,
            "max_backoff_minutes": 30.0,
            "max_logs_per_proxy": 50,
        },
    }
    ids: dict[str, int] = {}
    for kind, params in presets.items():
        cfg = call("POST", "/strategies", state=state, expect=201, json={
            "name": f"e2e-{kind}-{tag}",
            "kind": kind,
            "description": "Created by e2e test",
            "parameters": params,
        })
        remember(state, "strategies", cfg["id"])
        ids[kind] = cfg["id"]
    ok(f"created {len(ids)} strategy presets (one per kind)", state)
    return ids


def phase_group(state: State, strategy_id: int) -> int:
    step("Proxy group")
    name = f"e2e-group-{secrets.token_hex(3)}"
    group = call("POST", "/groups", state=state, expect=201, json={
        "name": name,
        "description": "Created by e2e test",
        "default_strategy_id": strategy_id,
        "proxy_ids": [],
    })
    remember(state, "groups", group["id"])
    ok(f"created group #{group['id']} ({name})", state)
    return group["id"]


def phase_proxies(state: State, provider_id: int, group_id: int) -> list[int]:
    step("Proxies (bulk import)")
    rows = [
        {"host": f"10.0.0.{i}", "port": 8080 + i, "protocol": "http",
         "username": f"u{i}", "password": f"p{i}"}
        for i in range(1, 6)
    ]
    created = call("POST", "/proxies/bulk", state=state, expect=201, json={
        "provider_id": provider_id,
        "group_ids": [group_id],
        "proxies": rows,
    })
    ids = [p["id"] for p in created]
    for pid in ids:
        remember(state, "proxies", pid)
    ok(f"bulk-imported {len(ids)} proxies into group #{group_id}", state)

    # Patch one to set an expiration date in 3 days (tests `expiring_in_days` filter).
    from datetime import datetime, timedelta, timezone
    soon = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    call("PATCH", f"/proxies/{ids[0]}", state=state, json={"expires_at": soon})
    expiring = call("GET", "/proxies", state=state, params={"expiring_in_days": 7})
    assert any(p["id"] == ids[0] for p in expiring), "expiring filter did not return tagged proxy"
    ok("expiring_in_days filter returns the tagged proxy", state)
    return ids


def phase_robot(state: State, group_id: int) -> tuple[int, str]:
    step("Robot")
    name = f"e2e-robot-{secrets.token_hex(3)}"
    robot = call("POST", "/robots", state=state, expect=201, json={
        "name": name,
        "description": "Created by e2e test",
        "group_ids": [group_id],
        "default_lease_minutes": 2,
    })
    remember(state, "robots", robot["id"])
    api_key = robot["api_key"]
    assert api_key, "robot must come back with api_key"
    state.robot_api_key = api_key
    ok(f"created robot #{robot['id']} ({name}) with api_key ({len(api_key)} chars)", state)

    rotated = call("POST", f"/robots/{robot['id']}/rotate-key", state=state)
    assert rotated["api_key"] != api_key
    state.robot_api_key = rotated["api_key"]
    ok("rotated robot api_key", state)
    return robot["id"], state.robot_api_key


def phase_domain(state: State) -> int:
    step("Domains")
    hostname = f"e2e-{secrets.token_hex(2)}.example.com"
    domain = call("POST", "/domains", state=state, expect=201, json={
        "hostname": hostname,
        "rate_limit_per_minute": 60,
        "notes": "e2e",
    })
    remember(state, "domains", domain["id"])
    ok(f"created domain #{domain['id']} ({hostname})", state)
    return domain["id"]


# ---------- robot simulation ---------------------------------------------------


def simulate_robot(state: State, group_id: int, iterations: int, strategy_ids: dict[str, int]) -> None:
    step(f"Simulating robot ({iterations} requests across {len(strategy_ids)} strategies)")
    targets = [
        "https://example.com/products",
        "https://example.com/listing/1",
        "https://example.com/listing/2",
        "https://api.example.com/v1/items",
    ]
    bot_headers = {"X-Robot-Key": state.robot_api_key}
    success_count = 0
    failure_count = 0
    strategy_pool = list(strategy_ids.values())

    for i in range(iterations):
        target = random.choice(targets)
        # Rotate across strategies so the comparison view has data for each.
        strategy_id = random.choice(strategy_pool)
        try:
            acq = requests.post(
                f"{API}/rotation/acquire",
                headers=bot_headers,
                json={"target_url": target, "group_id": group_id, "strategy_id": strategy_id},
                timeout=10,
            )
        except Exception as exc:
            fail(f"iteration {i+1}: acquire failed", state, exc)
            return
        if acq.status_code != 200:
            fail(f"iteration {i+1}: acquire returned {acq.status_code}", state, acq.text[:200])
            return
        lease = acq.json()
        lease_id = lease["lease_id"]
        proxy_id = lease["proxy"]["id"]

        # Simulate scraping outcome.
        # Proxies with id % 5 == 0 are the "bad" ones — higher failure rate.
        roll = random.random()
        if proxy_id % 5 == 0:
            success = roll < 0.4
        else:
            success = roll < 0.88
        status_code = random.choice([200, 200, 200, 200, 301]) if success \
            else random.choice([403, 403, 429, 500, 502, 503])
        duration_ms = random.uniform(80, 1500)

        rel = requests.post(
            f"{API}/rotation/release",
            headers=bot_headers,
            json={
                "lease_id": lease_id,
                "success": success,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "error_message": None if success else "simulated upstream rejection",
            },
            timeout=10,
        )
        if rel.status_code != 200:
            fail(f"iteration {i+1}: release returned {rel.status_code}", state, rel.text[:200])
            return

        if success:
            success_count += 1
        else:
            failure_count += 1

        # Light pacing so timestamps spread enough to populate the timeseries chart.
        time.sleep(0.05)

    rate = success_count / (success_count + failure_count) if iterations else 0
    ok(f"robot ran {iterations} requests — {success_count} ok / {failure_count} fail ({rate:.0%})", state)


# ---------- assertions on metrics ---------------------------------------------


def phase_metrics(state: State, group_id: int, robot_id: int) -> None:
    step("Metrics")
    summary = call("GET", "/metrics/summary", state=state, params={"group_id": group_id})
    assert summary["total_requests"] > 0, "summary.total_requests should be > 0 after the robot ran"
    ok(f"summary: {summary['total_requests']} requests, "
       f"{summary['success_rate']*100:.1f}% success, "
       f"avg {summary['average_duration_ms']:.0f}ms", state)

    ts = call("GET", "/metrics/timeseries", state=state,
              params={"group_id": group_id, "interval": "minute"})
    assert len(ts) >= 1, "expected at least one timeseries bucket"
    ok(f"timeseries returned {len(ts)} bucket(s)", state)

    sc = call("GET", "/metrics/status-codes", state=state, params={"group_id": group_id})
    assert len(sc) >= 1
    ok(f"status-code distribution returned {len(sc)} bucket(s)", state)

    top_robots = call("GET", "/metrics/top/robots", state=state, params={"group_id": group_id})
    assert any(r["total"] > 0 for r in top_robots), "expected at least one robot with traffic"
    ok(f"top robots returned {len(top_robots)} entr(y/ies)", state)

    top_proxies = call("GET", "/metrics/top/proxies", state=state, params={"group_id": group_id})
    assert any(p["total"] > 0 for p in top_proxies)
    ok(f"top proxies returned {len(top_proxies)} entr(y/ies)", state)

    logs = call("GET", "/logs", state=state, params={"robot_id": robot_id, "limit": 50})
    assert len(logs) > 0
    assert logs[0].get("strategy_kind"), "log rows should carry the strategy used"
    ok(f"GET /logs?robot_id={robot_id} returned {len(logs)} row(s) (with strategy)", state)

    # Comparison breakdowns across every dimension.
    for dim in ("strategy", "robot", "provider", "group", "host", "proxy"):
        rows = call("GET", "/metrics/breakdown", state=state,
                    params={"dimension": dim, "group_id": group_id})
        assert isinstance(rows, list)
        if dim == "strategy":
            assert len(rows) >= 2, "expected several strategies in the breakdown"
            summary = ", ".join(
                f"{r['label']}={r['success_rate']*100:.0f}%" for r in rows
            )
            ok(f"breakdown by strategy → {summary}", state)
        else:
            ok(f"breakdown by {dim} → {len(rows)} group(s)", state)


# ---------- negative paths -----------------------------------------------------


def phase_auth_negative(state: State) -> None:
    step("Negative auth paths")
    # Bad password
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=10)
    if r.status_code == 401:
        ok("wrong password → 401", state)
    else:
        fail(f"wrong password expected 401 got {r.status_code}", state)

    # No bearer
    r = requests.get(f"{API}/auth/me", timeout=10)
    if r.status_code == 401:
        ok("missing bearer → 401", state)
    else:
        fail(f"missing bearer expected 401 got {r.status_code}", state)

    # Bad robot key
    r = requests.post(f"{API}/rotation/acquire",
                      headers={"X-Robot-Key": "definitely-not-a-real-key"},
                      json={"target_url": "https://example.com"}, timeout=10)
    if r.status_code == 401:
        ok("bogus robot key → 401", state)
    else:
        fail(f"bogus robot key expected 401 got {r.status_code}", state)


# ---------- cleanup ------------------------------------------------------------


def cleanup(state: State) -> None:
    step("Cleanup")
    # Delete in dependency-safe order.
    order = ["robots", "proxies", "groups", "strategies", "providers", "domains"]
    for kind in order:
        for item_id in reversed(state.created.get(kind, [])):
            try:
                requests.delete(f"{API}/{kind}/{item_id}", headers=headers(state), timeout=10)
            except Exception:
                pass
        n = len(state.created.get(kind, []))
        if n:
            ok(f"removed {n} {kind}", state)


# ---------- main ---------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true",
                        help="Do not delete created entities at the end.")
    parser.add_argument("--robot", type=int, default=30,
                        help="Number of simulated robot iterations (default: 30).")
    args = parser.parse_args()

    print(f"{CYAN}ProxyOps E2E test{RESET}")
    print(f"  target:    {BASE_URL}")
    print(f"  admin:     {ADMIN_EMAIL}")
    print(f"  iterations: {args.robot}")

    state = State()

    try:
        phase_auth(state)
        provider_id = phase_provider(state)
        strategy_ids = phase_strategy(state)
        group_id = phase_group(state, strategy_ids["bayesian_beta"])
        phase_proxies(state, provider_id, group_id)
        robot_id, _ = phase_robot(state, group_id)
        phase_domain(state)
        simulate_robot(state, group_id, args.robot, strategy_ids)
        phase_metrics(state, group_id, robot_id)
        phase_auth_negative(state)
    except AssertionError as exc:
        fail("hard assertion", state, exc)
    finally:
        if args.keep:
            print(f"\n{YELLOW}--keep was passed; leaving created entities behind:{RESET}")
            for kind, ids in state.created.items():
                print(f"  {kind}: {ids}")
        else:
            cleanup(state)

    print()
    if state.failed == 0:
        print(f"{GREEN}all {state.passed} checks passed.{RESET}")
        return 0
    print(f"{RED}{state.failed} check(s) failed{RESET} ({state.passed} passed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
