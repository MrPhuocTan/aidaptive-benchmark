from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app import _render, get_db, _database_ready, _db_warning_payload, config
from src.database.repository import AsyncRepository

router = APIRouter()

@router.get("/reports", response_class=HTMLResponse)
async def page_reports(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    db_ok = _database_ready()
    completed_runs = []

    if db_ok:
        repo = AsyncRepository(session)
        try:
            runs = await repo.list_runs(limit=50)
            completed_runs = [r for r in runs if r.status == "completed"]
        except SQLAlchemyError:
            db_ok = False

    return _render(
        request,
        "reports.html",
        {
            "page": "reports",
            "config": config,
            "runs": completed_runs,
            "db_available": db_ok,
            **(_db_warning_payload() if not db_ok else {}),
        },
    )

@router.get("/reports/{run_id}", response_class=HTMLResponse)
async def page_report_details(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    db_ok = _database_ready()
    report_data = None
    run = None

    if db_ok:
        repo = AsyncRepository(session)
        try:
            run = await repo.get_run(run_id)
            if run:
                report_data = await repo.get_detailed_report_stats(run_id)
                chart_data = await repo.get_dashboard_chart_data(run_id)
                timeline_chart = await repo.get_timeline_chart_data(run_id)
        except SQLAlchemyError:
            db_ok = False

    if not run:
        return RedirectResponse(url="/reports")

    return _render(
        request,
        "report_details.html",
        {
            "page": "reports",
            "config": config,
            "run": run,
            "report_data": report_data,
            "chart_data": chart_data if run else None,
            "timeline_chart": timeline_chart if run else None,
            "db_available": db_ok,
            **(_db_warning_payload() if not db_ok else {}),
        },
    )

@router.get("/reports/{run_id}/download", response_class=HTMLResponse)
async def page_report_download(
    request: Request,
    run_id: str,
    session: AsyncSession = Depends(get_db),
):
    db_ok = _database_ready()
    report_data = None
    run = None

    if db_ok:
        repo = AsyncRepository(session)
        try:
            run = await repo.get_run(run_id)
            if run:
                report_data = await repo.get_detailed_report_stats(run_id)
                chart_data = await repo.get_dashboard_chart_data(run_id)
                timeline_chart = await repo.get_timeline_chart_data(run_id)
        except SQLAlchemyError:
            db_ok = False

    if not run:
        return RedirectResponse(url="/reports")

    response = _render(
        request,
        "report_standalone.html",
        {
            "run": run,
            "report_data": report_data,
            "chart_data": chart_data if run else None,
            "timeline_chart": timeline_chart if run else None,
        },
    )
    response.headers["Content-Disposition"] = f'attachment; filename="aidaptive_report_{run_id}.html"'
    return response
