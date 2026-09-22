import csv
import io
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select

from app.models import (
    Bid,
    BotSession,
    SessionError,
    SessionLocal,
    get_traceback,
    init_db,
)


def ensure_db() -> None:
    init_db()
    _end_stale_sessions()


def _end_stale_sessions() -> None:
    """Mark any sessions left as 'running' as 'crashed' (from killed processes)."""
    from datetime import datetime, timezone

    with SessionLocal() as db:
        stmt = select(BotSession).where(BotSession.status == "running")
        stale = db.scalars(stmt).all()
        now = datetime.now(timezone.utc)
        for s in stale:
            s.end_at = now
            s.status = "crashed"
            if not s.last_error:
                s.last_error = "Server was killed — session terminated"
        if stale:
            db.commit()


def get_bid_project_ids() -> set[str]:
    with SessionLocal() as session:
        rows = session.scalars(select(Bid.project_id)).all()
        return set(rows)


def get_processed_project_ids() -> set[str]:
    """Projects already bid on or successfully attempted — skipped can be re-checked."""
    with SessionLocal() as session:
        stmt = select(Bid.project_id).where(Bid.status.in_(("success", "failed")))
        rows = session.scalars(stmt).all()
        return set(rows)


def record_bid(
    project_id: str,
    title: str,
    url: str,
    category: str,
    status: str,
    bid_amount: float | None = None,
    currency: str | None = None,
    error_message: str | None = None,
) -> Bid:
    with SessionLocal() as session:
        existing = session.scalar(select(Bid).where(Bid.project_id == project_id))
        if existing:
            existing.title = title
            existing.url = url
            existing.category = category
            existing.status = status
            existing.bid_amount = bid_amount
            existing.currency = currency
            existing.error_message = error_message
            existing.bid_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(existing)
            return existing

        bid = Bid(
            project_id=project_id,
            title=title,
            url=url,
            category=category,
            status=status,
            bid_amount=bid_amount,
            currency=currency,
            error_message=error_message,
        )
        session.add(bid)
        session.commit()
        session.refresh(bid)
        return bid


def list_bids(limit: int = 500) -> list[Bid]:
    with SessionLocal() as session:
        stmt = select(Bid).order_by(Bid.bid_at.desc()).limit(limit)
        return list(session.scalars(stmt).all())


def count_bids_since(since: datetime) -> int:
    with SessionLocal() as session:
        stmt = select(Bid).where(
            Bid.bid_at >= since,
            Bid.status == "success",
        )
        return len(session.scalars(stmt).all())


def export_bids_csv() -> str:
    bids = list_bids()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "project_id", "title", "url", "category", "bid_amount", "currency", "status", "error_message", "bid_at"]
    )
    for b in bids:
        writer.writerow(
            [
                b.id,
                b.project_id,
                b.title,
                b.url,
                b.category,
                b.bid_amount,
                b.currency,
                b.status,
                b.error_message,
                b.bid_at.isoformat() if b.bid_at else "",
            ]
        )
    return output.getvalue()


def bids_today_count() -> int:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return count_bids_since(start)


def bids_last_hour_count() -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    return count_bids_since(since)


# ── Session tracking ──────────────────────────────────────────────

def create_session() -> int:
    with SessionLocal() as session:
        obj = BotSession()
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj.id


def end_session(session_id: int, status: str = "stopped") -> None:
    with SessionLocal() as db:
        obj = db.scalar(select(BotSession).where(BotSession.id == session_id))
        if obj:
            obj.end_at = datetime.now(timezone.utc)
            obj.status = status
            db.commit()


def update_session_bid_counts(session_id: int, success: bool) -> None:
    with SessionLocal() as db:
        obj = db.scalar(select(BotSession).where(BotSession.id == session_id))
        if obj:
            obj.total_bids = (obj.total_bids or 0) + 1
            if success:
                obj.successful_bids = (obj.successful_bids or 0) + 1
            else:
                obj.failed_bids = (obj.failed_bids or 0) + 1
            db.commit()


def record_session_error(
    session_id: int,
    error_type: str,
    error_message: str,
    context: str | None = None,
) -> int:
    with SessionLocal() as db:
        obj = SessionError(
            session_id=session_id,
            error_type=error_type,
            error_message=error_message,
            context=context,
            traceback=get_traceback(),
        )
        db.add(obj)

        sess = db.scalar(select(BotSession).where(BotSession.id == session_id))
        if sess:
            sess.last_error = error_message

        db.commit()
        db.refresh(obj)
        return obj.id


def list_sessions(limit: int = 20) -> list[BotSession]:
    with SessionLocal() as db:
        stmt = select(BotSession).order_by(desc(BotSession.id)).limit(limit)
        return list(db.scalars(stmt).all())


def list_session_errors(session_id: int | None = None, limit: int = 50) -> list[SessionError]:
    with SessionLocal() as db:
        stmt = select(SessionError)
        if session_id is not None:
            stmt = stmt.where(SessionError.session_id == session_id)
        stmt = stmt.order_by(desc(SessionError.id)).limit(limit)
        return list(db.scalars(stmt).all())
