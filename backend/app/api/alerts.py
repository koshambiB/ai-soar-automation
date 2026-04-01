"""
Alerts API - CRUD endpoints for the analyst dashboard
"""
from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
import logging

from ..core.database import get_connection, get_cursor

logger = logging.getLogger(__name__)
router = APIRouter(tags=["alerts"])


@router.get("/alerts")
def list_alerts(
    request:    Request,
    page:       int = Query(1, ge=1),
    page_size:  int = Query(20, ge=1, le=100),
    risk_level: Optional[str] = None,
    severity:   Optional[str] = None,
    status:     Optional[str] = None,
):
    """
    List alerts with optional filtering and pagination.
    Used by the dashboard main table.
    """
    offset = (page - 1) * page_size

    where_clauses = []
    params = []

    if risk_level:
        where_clauses.append("risk_level = %s")
        params.append(risk_level)
    if severity:
        where_clauses.append("severity = %s")
        params.append(severity)
    if status:
        where_clauses.append("status = %s")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    try:
        with get_connection() as conn:
            cur = get_cursor(conn)

            # Total count
            cur.execute(f"SELECT COUNT(*) as cnt FROM alerts {where_sql}", params)
            total = cur.fetchone()["cnt"]

            # Page of results
            cur.execute(
                f"""
                SELECT
                    id, alert_id, alert_timestamp, severity, source,
                    alert_type, status, rule_score, ml_prediction,
                    ml_confidence, risk_level, explanation,
                    created_at, updated_at
                FROM alerts
                {where_sql}
                ORDER BY alert_timestamp DESC
                LIMIT %s OFFSET %s
                """,
                params + [page_size, offset],
            )
            rows = cur.fetchall()

        return {
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "pages":     (total + page_size - 1) // page_size,
            "alerts":    rows,
        }

    except Exception as e:
        logger.error(f"list_alerts failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str, request: Request):
    """Get a single alert by alert_id including full raw_data and features."""
    try:
        with get_connection() as conn:
            cur = get_cursor(conn)
            cur.execute(
                "SELECT * FROM alerts WHERE alert_id = %s",
                [alert_id]
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        return row

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_alert failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/alerts/{alert_id}/status")
def update_alert_status(alert_id: str, body: dict, request: Request):
    """
    Update alert status (e.g. new → investigating → resolved).
    Called by analyst dashboard action buttons.
    """
    new_status = body.get("status")
    allowed = {"new", "investigating", "resolved", "false_positive"}

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {allowed}"
        )

    try:
        with get_connection() as conn:
            cur = get_cursor(conn)
            cur.execute(
                "UPDATE alerts SET status = %s WHERE alert_id = %s RETURNING alert_id, status",
                [new_status, alert_id]
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        return {"alert_id": row["alert_id"], "status": row["status"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"update_status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/stats/summary")
def get_stats(request: Request):
    """
    Aggregate stats for the dashboard header cards.
    Returns counts by risk_level, severity, status.
    """
    try:
        with get_connection() as conn:
            cur = get_cursor(conn)

            cur.execute("""
                SELECT
                    COUNT(*)                                          AS total,
                    COUNT(*) FILTER (WHERE risk_level = 'critical')  AS critical,
                    COUNT(*) FILTER (WHERE risk_level = 'high')      AS high,
                    COUNT(*) FILTER (WHERE risk_level = 'medium')    AS medium,
                    COUNT(*) FILTER (WHERE risk_level = 'low')       AS low,
                    COUNT(*) FILTER (WHERE risk_level = 'info')      AS info,
                    COUNT(*) FILTER (WHERE status = 'new')           AS new_alerts,
                    COUNT(*) FILTER (WHERE status = 'investigating') AS investigating,
                    COUNT(*) FILTER (WHERE status = 'resolved')      AS resolved
                FROM alerts
            """)
            stats = cur.fetchone()

            # Risk trend over last 24h (hourly buckets)
            cur.execute("""
                SELECT
                    DATE_TRUNC('hour', alert_timestamp) AS hour,
                    risk_level,
                    COUNT(*) AS count
                FROM alerts
                WHERE alert_timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY hour, risk_level
                ORDER BY hour
            """)
            trend = cur.fetchall()

        return {
            "summary": stats,
            "trend":   trend,
        }

    except Exception as e:
        logger.error(f"get_stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))