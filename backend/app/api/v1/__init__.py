from fastapi import APIRouter

from app.api.v1 import (
    auth,
    domains,
    groups,
    logs,
    metrics,
    providers,
    proxies,
    robots,
    rotation,
    strategies,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(proxies.router, prefix="/proxies", tags=["proxies"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(robots.router, prefix="/robots", tags=["robots"])
api_router.include_router(domains.router, prefix="/domains", tags=["domains"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(rotation.router, prefix="/rotation", tags=["rotation"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
