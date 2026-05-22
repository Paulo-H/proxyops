# Integrating a scraping robot with ProxyOps

A robot interacts with ProxyOps through two HTTP endpoints, authenticated with
its `X-Robot-Key` (returned once, when the robot is created in the UI or via
`POST /api/v1/robots`).

```
POST /api/v1/rotation/acquire    → lease a proxy for one outbound request
POST /api/v1/rotation/release    → report the outcome (and free the proxy)
```

### About the API key

- The raw key is shown **exactly once** — at creation and after `POST /robots/{id}/rotate-key`. Store it in the robot's environment (e.g. `PROXYOPS_ROBOT_KEY`); it cannot be retrieved later.
- The server never stores the raw key. It keeps only a **SHA-256 hash** (used for the indexed lookup on every request) plus a short non-secret `api_key_prefix` so the UI can show which key is which.
- If a key leaks, rotate it: the old key stops working immediately. To revoke access without rotating, set the robot to `is_active = false`.
- The key travels in a header, so **always use HTTPS in production**.

## Python — requests

```python
import os
import time
import requests

PROXYOPS = "http://proxyops:8000/api/v1"
HEADERS = {"X-Robot-Key": os.environ["PROXYOPS_ROBOT_KEY"]}


def fetch(target_url: str) -> requests.Response:
    acq = requests.post(
        f"{PROXYOPS}/rotation/acquire",
        headers=HEADERS,
        json={"target_url": target_url},
        timeout=10,
    ).json()

    lease_id = acq["lease_id"]
    p = acq["proxy"]
    proxy_url = (
        f"{p['protocol']}://{p['username']}:{p['password']}@{p['host']}:{p['port']}"
        if p["username"]
        else f"{p['protocol']}://{p['host']}:{p['port']}"
    )

    started = time.perf_counter()
    error = None
    status = None
    try:
        r = requests.get(target_url, proxies={"http": proxy_url, "https": proxy_url}, timeout=20)
        status = r.status_code
        success = 200 <= r.status_code < 400
        return r
    except Exception as exc:
        success = False
        error = str(exc)
        raise
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        requests.post(
            f"{PROXYOPS}/rotation/release",
            headers=HEADERS,
            json={
                "lease_id": lease_id,
                "success": success,
                "status_code": status,
                "duration_ms": duration_ms,
                "error_message": error,
            },
            timeout=5,
        )
```

## Choosing a strategy per request

You can override the group's default strategy on a single call:

```python
acq = requests.post(
    f"{PROXYOPS}/rotation/acquire",
    headers=HEADERS,
    json={
        "target_url": "https://example.com/page",
        "strategy_id": 42,          # any preset you created in the UI
        "lease_minutes": 3,         # tighter lease for fast endpoints
    },
).json()
```

## Choosing a specific group

If your robot is bound to several groups, pass `group_id`:

```python
{"target_url": "...", "group_id": 7}
```

If the robot is bound to exactly one group, that group is used implicitly.
