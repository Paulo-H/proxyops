# ProxyOps architecture

## Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                          docker-compose stack                       │
│                                                                     │
│   ┌────────────┐    /api    ┌──────────────┐     SQL    ┌────────┐  │
│   │ frontend   │ ────────▶ │   backend    │ ────────▶  │  db    │  │
│   │ nginx +    │            │   FastAPI    │            │  pg16  │  │
│   │ Vue 3 SPA  │            │              │            │        │  │
│   └────────────┘            └──────────────┘            └────────┘  │
│        ▲                          ▲                                 │
│        │ users via browser        │ robots via X-Robot-Key          │
└────────┼──────────────────────────┼─────────────────────────────────┘
         │                          │
   web UI session             scraping fleet
```

## Data model

```
User ── role={admin,operator,viewer}

Provider ──┬── n proxies
           │
Proxy   ──┬── many-to-many ── ProxyGroup ──┬── many-to-many ── Robot
          │                                │
          └── n RequestLog ◀─── n ProxyLease (audit trail of a rotation)

StrategyConfig (kind + parameters JSON)
  ▲
  └── default_strategy_id on ProxyGroup
```

Each RequestLog stores: proxy_id, group_id, robot_id, robot_name, target_url,
target_host, status_code, success, duration_ms, error_message, created_at.
Indices make filtering by `(robot, created_at)` and `(proxy, created_at)` fast
enough for live dashboards.

## Rotation lifecycle

```
robot                 backend                       db
  │  POST /acquire        │                          │
  │ ─────────────────────▶│                          │
  │                       │ resolve group + strategy │
  │                       │ select_candidate_proxy   │
  │                       │ lock proxy (lease ttl)   │
  │                       │ insert ProxyLease ───────▶│
  │ ◀───── lease_id, proxy credentials              │
  │                                                  │
  │  outbound HTTPS through proxy                    │
  │                                                  │
  │  POST /release        │                          │
  │ ─────────────────────▶│ insert RequestLog ──────▶│
  │                       │ unlock proxy, mark lease │
  │ ◀───── log_id                                    │
```

A lease that is never released is reaped automatically by `clean_expired_locks`
on the next `/acquire` call.

## Strategy plug-in surface

Every strategy implements:

```python
class ProxySelectionStrategy(ABC):
    kind: str

    def select(self, db, robot_name, target_url, target_host, group_id) -> Proxy | None: ...
```

Parameters are declared in `services/strategies/registry.py` so the UI form on
the Strategies page can render the right inputs with the right validation.
