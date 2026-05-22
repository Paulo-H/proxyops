from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentRobot
from app.db.session import get_db
from app.schemas import (
    AcquireRequest,
    AcquireResponse,
    ProxyCredentials,
    ReleaseRequest,
    ReleaseResponse,
)
from app.services.rotation import acquire_proxy, release_proxy

router = APIRouter()


@router.post(
    "/acquire",
    response_model=AcquireResponse,
    summary="Acquire a proxy for a scraping request",
    description=(
        "Called by a robot before issuing an outbound request. Returns the chosen proxy's "
        "credentials and a `lease_id` that must be sent back via `/release` once the request "
        "completes (success or failure). The lease auto-expires after the robot's "
        "`default_lease_minutes` if not released."
    ),
)
def acquire(
    body: AcquireRequest,
    robot: CurrentRobot,
    db: Session = Depends(get_db),
) -> AcquireResponse:
    proxy, lease, kind = acquire_proxy(
        db=db,
        robot=robot,
        target_url=body.target_url,
        requested_group_id=body.group_id,
        strategy_id=body.strategy_id,
        lease_minutes=body.lease_minutes,
    )
    return AcquireResponse(
        lease_id=lease.id,
        proxy=ProxyCredentials(
            id=proxy.id,
            host=proxy.host,
            port=proxy.port,
            protocol=proxy.protocol,
            username=proxy.username,
            password=proxy.password,
        ),
        strategy=kind,
        group_id=lease.group_id,
    )


@router.post(
    "/release",
    response_model=ReleaseResponse,
    summary="Report the outcome of a scraping request",
    description=(
        "Releases the proxy back to the pool and records the request log. The fields "
        "`success`, `status_code`, `duration_ms`, and `error_message` feed the metrics "
        "dashboards and inform future selection decisions (e.g. Bayesian Beta posteriors)."
    ),
)
def release(
    body: ReleaseRequest,
    robot: CurrentRobot,
    db: Session = Depends(get_db),
) -> ReleaseResponse:
    log = release_proxy(
        db=db,
        robot=robot,
        lease_id=body.lease_id,
        success=body.success,
        status_code=body.status_code,
        duration_ms=body.duration_ms,
        error_message=body.error_message,
    )
    return ReleaseResponse(ok=True, log_id=log.id)
