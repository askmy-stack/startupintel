"""Term sheet analysis API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from sqlalchemy import select

from startupintel.api.dependencies import DbDep, get_startup_or_404
from startupintel.api.schemas import TermBotOutput, ClauseAnalysis
from startupintel.bots.term_bot import TermBot
from startupintel.db.models import TermSheetAnalysis, Startup
from startupintel.events.producer import InMemoryEventProducer

router = APIRouter(prefix="/termsheet", tags=["termsheets"])


@router.post("/analyze", response_model=TermBotOutput)
async def analyze_termsheet_text(
    text: str,
    startup_id: UUID | None = None,
) -> TermBotOutput:
    """Analyze term sheet text."""
    bot = TermBot(producer=InMemoryEventProducer())
    result = await bot.analyze_text(text, startup_id)

    return TermBotOutput(
        analysis_id=result.analysis_id,
        startup_id=result.startup_id,
        founder_friendliness_score=result.founder_friendliness_score,
        market_benchmark_score=result.market_benchmark_score,
        red_flags=result.red_flags,
        yellow_flags=result.yellow_flags,
        clause_scores={
            name: ClauseAnalysis(
                detected_value=analysis.detected_value,
                is_market_standard=analysis.is_market_standard,
                risk_level=analysis.risk_level,
                explanation=analysis.explanation,
                founder_impact=analysis.founder_impact,
                weight=analysis.weight,
                score=analysis.score,
            )
            for name, analysis in result.clause_scores.items()
        },
        llm_diagnosis=result.llm_diagnosis,
        analyzed_at=result.analyzed_at,
    )


@router.post("/analyze-file", response_model=TermBotOutput)
async def analyze_termsheet_file(
    file: UploadFile = File(...),
    startup_id: UUID | None = None,
) -> TermBotOutput:
    """Analyze uploaded term sheet file."""
    # Read file content
    content = await file.read()

    # Try to decode as text
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        # Try other encodings or raise error
        try:
            text = content.decode("latin-1")
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode file. Please provide text-based term sheet.",
            )

    return await analyze_termsheet_text(text, startup_id)


@router.post("/startup/{startup_id}/analyze", response_model=TermBotOutput)
async def analyze_startup_termsheet(
    startup_id: UUID,
    text: str,
    db: DbDep,
) -> TermBotOutput:
    """Analyze term sheet for a specific startup."""
    startup = await get_startup_or_404(db, startup_id)

    bot = TermBot(producer=InMemoryEventProducer())
    result = await bot.analyze_text(text, startup_id)

    # Save to database
    analysis = TermSheetAnalysis(
        startup_id=startup_id,
        raw_text=text[:10000],  # Truncate if too long
        founder_friendliness_score=result.founder_friendliness_score,
        red_flags=result.red_flags,
        clause_scores={name: {
            "detected_value": a.detected_value,
            "risk_level": a.risk_level,
            "score": a.score,
        } for name, a in result.clause_scores.items()},
        market_benchmark={},
        llm_diagnosis=result.llm_diagnosis,
    )
    db.add(analysis)
    await db.commit()

    return TermBotOutput(
        analysis_id=result.analysis_id,
        startup_id=result.startup_id,
        founder_friendliness_score=result.founder_friendliness_score,
        market_benchmark_score=result.market_benchmark_score,
        red_flags=result.red_flags,
        yellow_flags=result.yellow_flags,
        clause_scores={
            name: ClauseAnalysis(
                detected_value=analysis.detected_value,
                is_market_standard=analysis.is_market_standard,
                risk_level=analysis.risk_level,
                explanation=analysis.explanation,
                founder_impact=analysis.founder_impact,
                weight=analysis.weight,
                score=analysis.score,
            )
            for name, analysis in result.clause_scores.items()
        },
        llm_diagnosis=result.llm_diagnosis,
        analyzed_at=result.analyzed_at,
    )


@router.get("/startup/{startup_id}/history")
async def get_termsheet_history(
    startup_id: UUID,
    db: DbDep,
    limit: int = 10,
) -> list[dict]:
    """Get term sheet analysis history for a startup."""
    startup = await get_startup_or_404(db, startup_id)

    result = await db.execute(
        select(TermSheetAnalysis)
        .where(TermSheetAnalysis.startup_id == startup_id)
        .order_by(TermSheetAnalysis.analyzed_at.desc())
        .limit(limit)
    )
    analyses = result.scalars().all()

    return [
        {
            "id": a.id,
            "founder_friendliness_score": a.founder_friendliness_score,
            "red_flags": a.red_flags,
            "analyzed_at": a.analyzed_at,
        }
        for a in analyses
    ]


@router.get("/clauses/standards")
async def get_clause_standards() -> dict:
    """Get market standard clauses information."""
    from startupintel.bots.term_bot import CLAUSES

    return {
        "total_clauses": len(CLAUSES),
        "clauses": {
            name: {
                "weight": clause["weight"],
                "standard": clause["standard"],
                "red_flags": clause["red_flags"],
            }
            for name, clause in CLAUSES.items()
        },
    }
