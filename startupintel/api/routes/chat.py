"""Chat API routes for a conversational interface over the bots."""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from startupintel.api.dependencies import (
    DbDep,
    get_llm_client,
    get_redis_client,
    rate_limit_dependency,
)
from startupintel.db.models import Startup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_MAX_MESSAGE_LENGTH = 4000
_CONVERSATION_TTL_HOURS = 24
_USE_REDIS = os.getenv("USE_REDIS_CONVERSATIONS", "false").lower() == "true"

# In-memory fallback conversation store: id -> (context, last_seen).
_conversations: dict[str, tuple["ConversationContext", datetime]] = {}


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def sanitize_input(text: str) -> str:
    """Strip HTML/script vectors and normalize whitespace in user input."""
    if not text:
        return ""
    text = text.replace("\x00", "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"on\w+\s*=", "", text, flags=re.IGNORECASE)
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)
    text = re.sub(r"data:", "", text, flags=re.IGNORECASE)
    text = re.sub(r"[\t\r\f\v]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=utc_now)
    metadata: dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request body for a chat turn."""

    message: str
    conversation_id: str | None = None
    context: dict = Field(default_factory=dict)
    role: str = Field(
        default="founder",
        pattern="^(founder|engineer|product|investor|analyst)$",
    )
    stream: bool = True


class ChatResponse(BaseModel):
    """Response for a completed (non-streaming) chat turn."""

    message: ChatMessage
    conversation_id: str
    suggested_actions: list[dict] = Field(default_factory=list)
    related_insights: list[dict] = Field(default_factory=list)
    bot_results: dict | None = None


_INTENT_KEYWORDS: dict[str, list[str]] = {
    "runway_analysis": ["runway", "stress", "financial", "funding", "cash", "burn"],
    "obituary_analysis": ["obituary", "failure", "risk", "danger", "problem"],
    "pmf_analysis": ["pmf", "product market fit", "traction", "growth", "adoption"],
    "pivot_analysis": ["pivot", "change", "direction", "strategy", "shift"],
    "acqui_analysis": ["acqui", "acquisition", "exit", "sell", "buyout"],
    "investor_analysis": ["investor", "network", "vc", "funding round"],
    "accelerator_analysis": ["accelerator", "incubator", "program", "yc"],
    "term_analysis": ["term sheet", "terms", "valuation", "equity", "clause"],
    "startup_search": ["find", "search", "startup", "company", "look up"],
    "compare": ["compare", "versus", "vs", "better", "difference"],
}

_SYSTEM_PROMPTS: dict[str, str] = {
    "founder": (
        "You are a startup intelligence advisor helping founders understand "
        "their company's health, risks, and opportunities. Provide actionable "
        "business insights and strategic recommendations."
    ),
    "engineer": (
        "You are a technical intelligence advisor helping engineering teams "
        "understand architecture, technical debt, and technology decisions."
    ),
    "product": (
        "You are a product intelligence advisor helping product teams "
        "understand adoption, feature decisions, and product strategy."
    ),
    "investor": (
        "You are an investment intelligence advisor helping investors evaluate "
        "startups with financial analysis and market insights."
    ),
    "analyst": (
        "You are a research analyst providing comprehensive, data-driven "
        "startup intelligence across all dimensions."
    ),
}


class ConversationContext:
    """Holds the message history and detected state for a conversation."""

    def __init__(self) -> None:
        self.history: list[ChatMessage] = []
        self.detected_intent: str | None = None
        self.user_role: str = "founder"
        self.entities: dict = {}

    def add_message(self, message: ChatMessage) -> None:
        self.history.append(message)

    def get_recent_context(self, n: int = 5) -> list[ChatMessage]:
        return self.history[-n:]

    def detect_intent(self, message: str) -> str:
        lowered = message.lower()
        for intent, keywords in _INTENT_KEYWORDS.items():
            if any(kw in lowered for kw in keywords):
                return intent
        return "general"


def _serialize_context(context: ConversationContext) -> str:
    return json.dumps(
        {
            "history": [msg.model_dump(mode="json") for msg in context.history],
            "detected_intent": context.detected_intent,
            "user_role": context.user_role,
            "entities": context.entities,
            "updated_at": utc_now().isoformat(),
        }
    )


def _deserialize_context(data: str) -> ConversationContext:
    parsed = json.loads(data)
    context = ConversationContext()
    context.history = [ChatMessage(**msg) for msg in parsed.get("history", [])]
    context.detected_intent = parsed.get("detected_intent")
    context.user_role = parsed.get("user_role") or "founder"
    context.entities = parsed.get("entities", {})
    return context


async def get_or_create_conversation(
    conversation_id: str | None,
    redis=None,
) -> tuple[str, ConversationContext]:
    """Load an existing conversation or create a fresh one.

    Uses Redis when ``USE_REDIS_CONVERSATIONS`` is enabled and a client is
    available; otherwise falls back to the in-memory store.
    """
    if _USE_REDIS and redis is not None:
        if conversation_id:
            data = await redis.get(f"chat:{conversation_id}")
            if data:
                return conversation_id, _deserialize_context(data)
        new_id = conversation_id or str(uuid4())
        context = ConversationContext()
        await redis.setex(
            f"chat:{new_id}",
            timedelta(hours=_CONVERSATION_TTL_HOURS),
            _serialize_context(context),
        )
        return new_id, context

    now = utc_now()
    expired = [
        key
        for key, (_, seen) in _conversations.items()
        if now - seen > timedelta(hours=_CONVERSATION_TTL_HOURS)
    ]
    for key in expired:
        del _conversations[key]

    if conversation_id and conversation_id in _conversations:
        context, _ = _conversations[conversation_id]
        _conversations[conversation_id] = (context, now)
        return conversation_id, context

    new_id = conversation_id or str(uuid4())
    context = ConversationContext()
    _conversations[new_id] = (context, now)
    return new_id, context


def format_bot_results(bot_results: dict | None) -> str:
    if not bot_results:
        return ""
    return f"\nBot analysis results:\n{bot_results}\n"


async def run_relevant_bot(intent: str, message: str, db: DbDep, llm) -> dict | None:
    """Run a bot for the detected intent.

    Placeholder: real startup-id extraction and bot orchestration land with the
    bot-run route slice. Returns ``None`` until then.
    """
    return None


async def generate_intelligent_response(
    message: str,
    intent: str,
    context: ConversationContext,
    llm,
    db: DbDep,
    role: str,
    system_prompt: str,
) -> str:
    """Build a prompt from history + intent and return the LLM completion."""
    bot_results = None
    if intent in {
        "runway_analysis",
        "obituary_analysis",
        "pmf_analysis",
        "pivot_analysis",
        "acqui_analysis",
    }:
        bot_results = await run_relevant_bot(intent, message, db, llm)

    recent = context.get_recent_context(3)
    history_text = "\n".join(f"{m.role}: {m.content}" for m in recent[:-1])

    prompt = (
        f"{system_prompt}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"User message: {message}\n\n"
        f"Detected intent: {intent}\n"
        f"User role: {role}\n\n"
        f"{format_bot_results(bot_results)}\n\n"
        "Provide a helpful, natural response. Be conversational but informative. "
        "If this is a follow-up question, reference previous context. Suggest "
        "relevant next steps.\n\nResponse:"
    )

    try:
        return await llm.complete(prompt, temperature=0.7, max_tokens=1024)
    except Exception:
        readable = intent.replace("_", " ")
        return (
            "I'm here to help with your startup intelligence needs. I noticed "
            f"you're asking about {readable}. Could you tell me which startup "
            "you'd like me to analyze?"
        )


def generate_suggested_actions(intent: str, context: ConversationContext) -> list[dict]:
    actions = {
        "runway_analysis": [
            {"label": "View detailed runway metrics", "action": "run_bot", "bot": "runway"},
            {"label": "Compare with similar startups", "action": "compare"},
            {"label": "Get funding recommendations", "action": "advice"},
        ],
        "obituary_analysis": [
            {"label": "View failure pattern analysis", "action": "run_bot", "bot": "obituary"},
            {"label": "See risk mitigation strategies", "action": "advice"},
            {"label": "Compare with failed startups", "action": "compare"},
        ],
        "pmf_analysis": [
            {"label": "View PMF metrics", "action": "run_bot", "bot": "pmf"},
            {"label": "See growth recommendations", "action": "advice"},
            {"label": "Analyze user feedback", "action": "analyze"},
        ],
        "pivot_analysis": [
            {"label": "View pivot history", "action": "run_bot", "bot": "pivot"},
            {"label": "Explore alternative strategies", "action": "explore"},
            {"label": "Get strategic advice", "action": "advice"},
        ],
        "acqui_analysis": [
            {"label": "View acqui-hire probability", "action": "run_bot", "bot": "acqui"},
            {"label": "See likely acquirers", "action": "analyze"},
            {"label": "Get exit strategy advice", "action": "advice"},
        ],
        "startup_search": [
            {"label": "View startup details", "action": "view"},
            {"label": "Run full analysis", "action": "analyze_all"},
            {"label": "Add to watchlist", "action": "watch"},
        ],
        "general": [
            {"label": "Search startups", "action": "search"},
            {"label": "View dashboard", "action": "dashboard"},
            {"label": "Get help", "action": "help"},
        ],
    }
    return actions.get(intent, actions["general"])


async def generate_related_insights(intent: str, db: DbDep) -> list[dict]:
    insights: list[dict] = []
    try:
        result = await db.execute(select(Startup).limit(3))
        for startup in result.scalars().all():
            insights.append(
                {
                    "type": "startup",
                    "title": startup.name,
                    "description": (
                        f"{startup.industry or 'Tech'} startup at "
                        f"{startup.stage or 'early'} stage"
                    ),
                    "relevance_score": 0.85,
                }
            )
    except Exception:
        logger.debug("related insights lookup failed", exc_info=True)
    return insights


@router.post(
    "/send",
    response_model=ChatResponse,
    dependencies=[Depends(rate_limit_dependency)],
)
async def send_message(
    request: ChatRequest,
    db: DbDep,
    redis=Depends(get_redis_client),
) -> ChatResponse:
    """Send a message and get a full (non-streaming) assistant response."""
    sanitized = sanitize_input(request.message)
    if len(sanitized) > _MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message too long. Maximum {_MAX_MESSAGE_LENGTH} characters allowed.",
        )
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    conversation_id, context = await get_or_create_conversation(
        request.conversation_id, redis
    )
    context.user_role = request.role
    context.add_message(ChatMessage(role="user", content=sanitized))

    intent = context.detect_intent(sanitized)
    context.detected_intent = intent

    llm = get_llm_client()
    response_content = await generate_intelligent_response(
        message=sanitized,
        intent=intent,
        context=context,
        llm=llm,
        db=db,
        role=request.role,
        system_prompt=_SYSTEM_PROMPTS.get(request.role, _SYSTEM_PROMPTS["founder"]),
    )

    assistant_message = ChatMessage(
        role="assistant",
        content=response_content,
        metadata={"intent": intent, "role": request.role},
    )
    context.add_message(assistant_message)

    if _USE_REDIS and redis is not None:
        await redis.setex(
            f"chat:{conversation_id}",
            timedelta(hours=_CONVERSATION_TTL_HOURS),
            _serialize_context(context),
        )

    return ChatResponse(
        message=assistant_message,
        conversation_id=conversation_id,
        suggested_actions=generate_suggested_actions(intent, context),
        related_insights=await generate_related_insights(intent, db),
    )


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    db: DbDep,
    redis=Depends(get_redis_client),
) -> StreamingResponse:
    """Stream an assistant response as server-sent events."""
    sanitized = sanitize_input(request.message)
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    conversation_id, context = await get_or_create_conversation(
        request.conversation_id, redis
    )
    context.user_role = request.role
    context.add_message(ChatMessage(role="user", content=sanitized))
    intent = context.detect_intent(sanitized)
    context.detected_intent = intent

    async def generate_stream() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation_id})}\n\n"
        for chunk in (
            "I'm analyzing your request",
            f" about {intent.replace('_', ' ')}...",
            "\n\n",
        ):
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

        llm = get_llm_client()
        full_response = await generate_intelligent_response(
            message=sanitized,
            intent=intent,
            context=context,
            llm=llm,
            db=db,
            role=request.role,
            system_prompt=_SYSTEM_PROMPTS.get(request.role, _SYSTEM_PROMPTS["founder"]),
        )
        context.add_message(ChatMessage(role="assistant", content=full_response))
        yield f"data: {json.dumps({'type': 'complete', 'content': full_response})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str) -> list[ChatMessage]:
    """Return the message history for an in-memory conversation."""
    if conversation_id not in _conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or expired",
        )
    context, _ = _conversations[conversation_id]
    return context.history


@router.post("/conversations/{conversation_id}/clear")
async def clear_conversation(conversation_id: str) -> dict:
    """Clear the history of an in-memory conversation."""
    if conversation_id not in _conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or expired",
        )
    context, _ = _conversations[conversation_id]
    context.history.clear()
    _conversations[conversation_id] = (context, utc_now())
    return {"message": "Conversation cleared", "conversation_id": conversation_id}


@router.get("/intents")
async def get_available_intents() -> dict:
    """List supported intents and their descriptions."""
    return {
        "runway_analysis": "Analyze financial runway and stress indicators",
        "obituary_analysis": "Detect failure patterns and risks",
        "pmf_analysis": "Evaluate product-market fit",
        "pivot_analysis": "Detect strategic pivots and changes",
        "acqui_analysis": "Predict acquisition probability",
        "investor_analysis": "Analyze investor network and value-add",
        "accelerator_analysis": "Compare accelerator programs",
        "term_analysis": "Analyze term sheets and clauses",
        "startup_search": "Find and explore startups",
        "compare": "Compare multiple startups",
        "general": "General questions and help",
    }
