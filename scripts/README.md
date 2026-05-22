# scripts/

End-to-end and helper scripts.

## `test_e2e.py`

Smoke-tests every router against a running ProxyOps stack and simulates a
scraping robot so the dashboard ends up with realistic data.

```bash
pip install requests
python scripts/test_e2e.py
```

What it exercises:

1. `POST /auth/login` + `GET /auth/me`
2. CRUD on **providers**, **strategy presets**, **proxy groups**, **proxies**
   (incl. bulk import + `expiring_in_days` filter), **robots** (incl. API-key
   rotation), **domains**.
3. Robot flow: `acquire` → simulate outcome → `release`, ran N times (default
   30). Some proxy IDs are deliberately "bad" so the success rate is non-trivial.
4. Metrics: `/metrics/summary`, `/timeseries`, `/status-codes`, `/top/robots`,
   `/top/proxies`, plus `/logs`.
5. Negative paths: wrong password, missing bearer, bogus robot key.
6. Cleans everything it created (unless `--keep`).

### Options

| Flag                  | Meaning                                                   |
| --------------------- | --------------------------------------------------------- |
| `--keep`              | Don't delete entities at the end — useful for inspecting in the UI. |
| `--robot N`           | Number of robot iterations (default 30).                  |
| `BASE_URL=...`        | API root (default `http://localhost:8000`).               |
| `ADMIN_EMAIL=...`     | Seeded admin email (default `admin@proxyops.io`).         |
| `ADMIN_PASSWORD=...`  | Seeded admin password (default `changeme`).               |

### Example

```bash
# 200 robot requests, keep entities around to inspect the dashboard
python scripts/test_e2e.py --robot 200 --keep
```

Exit code is `0` on full pass, `1` if any check failed.
