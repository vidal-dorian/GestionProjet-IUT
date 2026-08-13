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

RECENT_ENTRIES_LIMIT = 10


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


@router.get("/recent-entries", response_model=list[schemas.RecentTimeEntry])
def recent_entries(project_id: int, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    return crud.list_recent_time_entries_for_project(db, project_id, RECENT_ENTRIES_LIMIT)


@router.get("/hours-by-issue", response_model=schemas.HoursByIssue)
def hours_by_issue(project_id: int, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    rows = crud.sum_hours_by_github_issue(db, project_id)
    items = [
        schemas.HoursByIssueItem(
            issue_number=issue.number, issue_title=issue.title, issue_url=issue.url, hours=round(hours, 2)
        )
        for issue, hours in rows
    ]
    items.sort(key=lambda item: item.hours, reverse=True)

    return schemas.HoursByIssue(items=items, unattached_hours=round(crud.sum_unattached_hours(db, project_id), 2))


@router.get("/stats", response_model=schemas.ProjectStats)
def project_stats(project_id: int, db: Session = Depends(get_db)):
    if crud.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    member_count = crud.count_members(db, project_id)
    total_hours = crud.sum_project_hours(db, project_id)
    average = round(total_hours / member_count, 2) if member_count else 0.0

    return schemas.ProjectStats(
        total_hours=round(total_hours, 2),
        member_count=member_count,
        active_member_count=crud.count_active_members(db, project_id),
        entry_count=crud.count_time_entries(db, project_id),
        average_hours_per_member=average,
    )
