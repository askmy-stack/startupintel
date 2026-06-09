"""Export functionality for CSV, JSON, and Excel downloads."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from startupintel.api.dependencies import DbDep
from startupintel.db.models import Startup, StartupScore

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/startups/csv")
async def export_startups_csv(
    db: DbDep,
    industry: str | None = Query(None, description="Filter by industry"),
    stage: str | None = Query(None, description="Filter by stage"),
) -> StreamingResponse:
    """Export startups to CSV format."""
    # Build query
    stmt = select(Startup)
    if industry:
        stmt = stmt.where(Startup.industry.ilike(f"%{industry}%"))
    if stage:
        stmt = stmt.where(Startup.stage == stage)
    
    result = await db.execute(stmt)
    startups = result.scalars().all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "id", "name", "domain", "industry", "stage", "founded_year",
        "hq_city", "hq_country", "employee_count", "total_funding_usd",
        "last_funding_date", "created_at", "updated_at",
    ])
    
    # Write data
    for startup in startups:
        writer.writerow([
            str(startup.id),
            startup.name,
            startup.domain,
            startup.industry or "",
            startup.stage or "",
            startup.founded_year or "",
            startup.hq_city or "",
            startup.hq_country or "",
            startup.employee_count or "",
            startup.total_funding_usd or "",
            startup.last_funding_date.isoformat() if startup.last_funding_date else "",
            startup.created_at.isoformat() if startup.created_at else "",
            startup.updated_at.isoformat() if startup.updated_at else "",
        ])
    
    # Create response
    output.seek(0)
    filename = f"startups_export_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/startups/json")
async def export_startups_json(
    db: DbDep,
    industry: str | None = Query(None, description="Filter by industry"),
    stage: str | None = Query(None, description="Filter by stage"),
    pretty: bool = Query(True, description="Pretty print JSON"),
) -> StreamingResponse:
    """Export startups to JSON format."""
    # Build query
    stmt = select(Startup)
    if industry:
        stmt = stmt.where(Startup.industry.ilike(f"%{industry}%"))
    if stage:
        stmt = stmt.where(Startup.stage == stage)
    
    result = await db.execute(stmt)
    startups = result.scalars().all()
    
    # Convert to dict
    data = []
    for startup in startups:
        data.append({
            "id": str(startup.id),
            "name": startup.name,
            "domain": startup.domain,
            "crunchbase_id": startup.crunchbase_id,
            "founded_year": startup.founded_year,
            "industry": startup.industry,
            "stage": startup.stage,
            "hq_city": startup.hq_city,
            "hq_country": startup.hq_country,
            "employee_count": startup.employee_count,
            "total_funding_usd": startup.total_funding_usd,
            "last_funding_date": startup.last_funding_date.isoformat() if startup.last_funding_date else None,
            "created_at": startup.created_at.isoformat() if startup.created_at else None,
            "updated_at": startup.updated_at.isoformat() if startup.updated_at else None,
        })
    
    # Create JSON output
    indent = 2 if pretty else None
    json_output = json.dumps({
        "exported_at": datetime.now(UTC).isoformat(),
        "count": len(data),
        "startups": data,
    }, indent=indent, default=str)
    
    filename = f"startups_export_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        io.BytesIO(json_output.encode()),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/startup/{startup_id}/report")
async def export_startup_report(
    startup_id: UUID,
    db: DbDep,
    format: str = Query("json", pattern="^(json|csv)$"),
) -> StreamingResponse:
    """Export comprehensive report for a single startup."""
    # Get startup
    from startupintel.api.dependencies import get_startup_or_404
    startup = await get_startup_or_404(db, startup_id)
    
    # Get scores
    scores_stmt = (
        select(StartupScore)
        .where(StartupScore.startup_id == startup_id)
        .order_by(StartupScore.computed_at.desc())
    )
    scores_result = await db.execute(scores_stmt)
    scores = scores_result.scalars().all()
    
    # Build report data
    report = {
        "startup": {
            "id": str(startup.id),
            "name": startup.name,
            "domain": startup.domain,
            "industry": startup.industry,
            "stage": startup.stage,
            "employee_count": startup.employee_count,
            "total_funding_usd": startup.total_funding_usd,
        },
        "scores": [
            {
                "bot_name": s.bot_name,
                "score": s.score,
                "signal_breakdown": s.signal_breakdown,
                "llm_diagnosis": s.llm_diagnosis,
                "computed_at": s.computed_at.isoformat() if s.computed_at else None,
            }
            for s in scores
        ],
        "generated_at": datetime.now(UTC).isoformat(),
    }
    
    if format == "json":
        json_output = json.dumps(report, indent=2, default=str)
        filename = f"{startup.name}_report_{datetime.now(UTC).strftime('%Y%m%d')}.json"
        return StreamingResponse(
            io.BytesIO(json_output.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    else:
        # CSV format
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Startup Report"])
        writer.writerow(["Generated", report["generated_at"]])
        writer.writerow([])
        
        writer.writerow(["Company Information"])
        for key, value in report["startup"].items():
            writer.writerow([key, value])
        writer.writerow([])
        
        writer.writerow(["Bot Scores"])
        writer.writerow(["Bot Name", "Score", "Computed At"])
        for score in report["scores"]:
            writer.writerow([
                score["bot_name"],
                score["score"],
                score["computed_at"],
            ])
        
        output.seek(0)
        filename = f"{startup.name}_report_{datetime.now(UTC).strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )


@router.get("/startups/template")
async def download_import_template() -> StreamingResponse:
    """Download CSV template for bulk importing startups."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header with example row
    writer.writerow([
        "name", "domain", "crunchbase_id", "founded_year",
        "industry", "stage", "hq_city", "hq_country",
        "employee_count", "total_funding_usd",
    ])
    
    # Example row
    writer.writerow([
        "TechCorp", "techcorp.com", "techcorp", "2020",
        "Software", "series_a", "San Francisco", "USA",
        "50", "15000000",
    ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=startup_import_template.csv"},
    )
