"""Reconcile stale queued/running versions that never finalized."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import AgentRun, AppVersion


FINAL_AGENT_STATUSES = {"done", "error"}
STALE_FINALIZATION_GRACE = timedelta(seconds=20)
STALE_QUEUE_GRACE = timedelta(minutes=5)
STALE_RUNNING_GRACE = timedelta(minutes=5)
STALE_QA_PREVIEW_GRACE = timedelta(seconds=90)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def reconcile_version_status(session: Session, version: AppVersion) -> AppVersion:
    if version.status not in {"queued", "running"}:
        return version
    if version.schema_json or version.code_json:
        return version

    runs = list(
        session.exec(
            select(AgentRun)
            .where(AgentRun.version_id == version.id)
            .order_by(AgentRun.id.asc())
        ).all()
    )

    now = datetime.now(timezone.utc)
    created_at = _as_utc(version.created_at) or now

    if not runs:
        if now - created_at > STALE_QUEUE_GRACE:
            version.status = "failed"
            session.add(version)
            session.commit()
            session.refresh(version)
        return version

    if any(run.status == "running" for run in runs):
        running_runs = [run for run in runs if run.status == "running"]
        running_since = max(
            _as_utc(run.started_at) or created_at
            for run in running_runs
        )
        grace = (
            STALE_QA_PREVIEW_GRACE
            if any(run.agent_name == "qa" for run in running_runs)
            else STALE_RUNNING_GRACE
        )
        if now - running_since > grace:
            version.status = "failed"
            session.add(version)
            session.commit()
            session.refresh(version)
        return version

    if all(run.status in FINAL_AGENT_STATUSES for run in runs):
        last_event = max(
            _as_utc(run.ended_at) or _as_utc(run.started_at) or created_at for run in runs
        )
        if now - last_event > STALE_FINALIZATION_GRACE:
            version.status = "failed"
            session.add(version)
            session.commit()
            session.refresh(version)
        return version

    if all(run.status == "pending" for run in runs) and now - created_at > STALE_QUEUE_GRACE:
        version.status = "failed"
        session.add(version)
        session.commit()
        session.refresh(version)

    return version


def reconcile_project_versions(session: Session, versions: list[AppVersion]) -> list[AppVersion]:
    return [reconcile_version_status(session, version) for version in versions]
