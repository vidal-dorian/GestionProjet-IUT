from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/api/projects/{project_id}/dashboard", tags=["dashboard"])

# Au-delà d'un mois d'étalement, une granularité journalière produirait un axe
# illisible : on bascule sur des points hebdomadaires (US-15).
DAILY_GRANULARITY_MAX_SPAN_DAYS = 31


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


@router.get("/hours-over-time", response_model=schemas.HoursOverTime)
def hours_over_time(project_id: int, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    entries = crud.list_time_entries_for_project(db, project_id)
    if not entries:
        return schemas.HoursOverTime(granularity="day", points=[])

    dates = [entry.date for entry in entries]
    span_days = (max(dates) - min(dates)).days + 1
    granularity = "day" if span_days <= DAILY_GRANULARITY_MAX_SPAN_DAYS else "week"

    totals: dict[date, float] = defaultdict(float)
    for entry in entries:
        bucket = entry.date if granularity == "day" else _week_start(entry.date)
        totals[bucket] += entry.duration_hours

    if granularity == "day":
        start, end, step = min(dates), max(dates), timedelta(days=1)
    else:
        start, end, step = _week_start(min(dates)), _week_start(max(dates)), timedelta(weeks=1)

    points = []
    cursor = start
    while cursor <= end:
        points.append(schemas.HoursOverTimePoint(period=cursor, hours=round(totals.get(cursor, 0.0), 2)))
        cursor += step

    return schemas.HoursOverTime(granularity=granularity, points=points)
