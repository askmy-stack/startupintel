"""Chat API routes for conversational interface."""

from __future__ import annotations

from datetime import datetime
from typing import AsyncGenerator
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from startupintel.api.dependencies import DbDep, get_llm_client, get_retriever
from startupintel.bots.runway_bot import RunwayBot
from startupintel.bots.obituary_bot import ObituaryBot
from startupintel.bots.pmf_bot import PMFBot
from startupintel.bots.pivot_bot import PivotBot
from startupintel.bots.acqui_bot import AcquiBot
from startupintel.bots.investor_bot import InvestorBot
from startupintel.bots.accelerator_bot import AcceleratorBot
from startupintel.bots.term_bot import TermBot
from startupintel.db.models import Startup
from startupintel.events.producer import InMemoryEventProducer
from sqlalchemy import select

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """A chat message."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Request for chat completion."""
    message: str
    conversation_id: str | None = None
    context: dict = Field(default_factory=dict)
    role: str = Field(default="founder", pattern="^(founder|engineer|product|investor|analyst)$")
    stream: bool = True


class ChatResponse(BaseModel):
    """Response from chat."""
    message: ChatMessage
    conversation_id: str
    suggested_actions: list[dict] = Field(default_factory=list)
    related_insights: list[dict] = Field(default_factory=list)
    bot_results: dict | None = None


class ConversationContext:
    """Manages conversation context and history."""
    
    def __init__(self):
        self.history: list[ChatMessage] = []
        self.context: dict = {}
        self.detected_intent: str | None = None
        self.active_bots: list[str] = []
        self.user_role: str = "founder"
        
    def add_message(self, message: ChatMessage):
        """Add message to history."""
        self.history.append(message)
        
    def get_recent_context(self, n: int = 5) -> list[ChatMessage]:
        """Get recent messages for context."""
        return self.history[-n:] if len(self.history) > n else self.history
    
    def detect_intent(self, message: str) -> str:
        """Detect user intent from message."""
        intents = {
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
        
        message_lower = message.lower()
        for intent, keywords in intents.items():
            if any(kw in message_lower for kw in keywords):
                return intent
        return "general"


# In-memory conversation store (use Redis in production)
_conversations: dict[str, ConversationContext] = {}


def get_or_create_conversation(conversation_id: str | None) -> tuple[str, ConversationContext]:
    """Get existing conversation or create new one."""
    if conversation_id and conversation_id in _conversations:
        return conversation_id, _conversations[conversation_id]
    
    new_id = conversation_id or str(uuid4())
    _conversations[new_id] = ConversationContext()
    return new_id, _conversations[new_id]


@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    db: DbDep,
) -> ChatResponse:
    """Send a message to the conversational AI."""
    conversation_id, context = get_or_create_conversation(request.conversation_id)
    context.user_role = request.role
    
    # Add user message
    user_message = ChatMessage(role="user", content=request.message)
    context.add_message(user_message)
    
    # Detect intent
    intent = context.detect_intent(request.message)
    context.detected_intent = intent
    
    # Get LLM client
    llm = get_llm_client()
    
    # Build system prompt based on role
    system_prompts = {
        "founder": "You are a startup intelligence advisor helping founders understand their company's health, risks, and opportunities. Provide actionable business insights and strategic recommendations.",
        "engineer": "You are a technical intelligence advisor helping engineering teams understand system architecture, technical debt, and technology decisions. Focus on technical implementation details.",
        "product": "You are a product intelligence advisor helping product teams understand user adoption, feature decisions, and product strategy. Focus on product metrics and user insights.",
        "investor": "You are an investment intelligence advisor helping investors evaluate startups. Provide financial analysis, market insights, and investment recommendations.",
        "analyst": "You are a research analyst providing comprehensive startup intelligence across all dimensions. Be thorough and data-driven in your analysis.",
    }
    
    # Generate response
    response_content = await generate_intelligent_response(
        message=request.message,
        intent=intent,
        context=context,
        llm=llm,
        db=db,
        role=request.role,
        system_prompt=system_prompts.get(request.role, system_prompts["founder"]),
    )
    
    # Add assistant message
    assistant_message = ChatMessage(
        role="assistant",
        content=response_content,
        metadata={"intent": intent, "role": request.role}
    )
    context.add_message(assistant_message)
    
    # Generate suggested actions based on intent
    suggested_actions = generate_suggested_actions(intent, context)
    
    # Generate related insights
    related_insights = await generate_related_insights(intent, db)
    
    return ChatResponse(
        message=assistant_message,
        conversation_id=conversation_id,
        suggested_actions=suggested_actions,
        related_insights=related_insights,
    )


@router.post("/stream")
async def stream_message(
    request: ChatRequest,
    db: DbDep,
) -> StreamingResponse:
    """Stream a message response for real-time updates."""
    conversation_id, context = get_or_create_conversation(request.conversation_id)
    context.user_role = request.role
    
    # Add user message
    user_message = ChatMessage(role="user", content=request.message)
    context.add_message(user_message)
    
    # Detect intent
    intent = context.detect_intent(request.message)
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        import json
        
        # Send conversation ID first
        yield f"data: {json.dumps({'type': 'conversation_id', 'id': conversation_id})}\n\n"
        
        # Simulate typing/thinking with progressive response
        llm = get_llm_client()
        
        # Build response chunks
        chunks = [
            "I'm analyzing your request",
            f" about {intent.replace('_', ' ')}...",
            "\n\n",
        ]
        
        for chunk in chunks:
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        # Generate full response
        full_response = await generate_intelligent_response(
            message=request.message,
            intent=intent,
            context=context,
            llm=llm,
            db=db,
            role=request.role,
            system_prompt="You are a helpful startup intelligence advisor.",
        )
        
        # Send complete message
        yield f"data: {json.dumps({'type': 'complete', 'content': full_response})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
    )


async def generate_intelligent_response(
    message: str,
    intent: str,
    context: ConversationContext,
    llm,
    db: DbDep,
    role: str,
    system_prompt: str,
) -> str:
    """Generate an intelligent response based on intent."""
    
    # Check if we need to run bots
    bot_results = None
    if intent in ["runway_analysis", "obituary_analysis", "pmf_analysis", "pivot_analysis", "acqui_analysis"]:
        bot_results = await run_relevant_bot(intent, message, db, llm)
    
    # Build context from recent history
    recent_context = context.get_recent_context(3)
    history_text = "\n".join([
        f"{msg.role}: {msg.content}" for msg in recent_context[:-1]  # Exclude current message
    ])
    
    # Construct prompt
    prompt = f"""{system_prompt}

Conversation history:
{history_text}

User message: {message}

Detected intent: {intent}
User role: {role}

{format_bot_results(bot_results) if bot_results else ""}

Provide a helpful, natural response. Be conversational but informative. If this is a follow-up question, reference previous context. Suggest relevant next steps or questions the user might want to ask.

Response:"""
    
    try:
        response = await llm.complete(prompt, temperature=0.7, max_tokens=1024)
        return response
    except Exception as e:
        return f"I'm here to help with your startup intelligence needs. I noticed you're asking about {intent.replace('_', ' ')}. Could you tell me which startup you'd like me to analyze?"


async def run_relevant_bot(intent: str, message: str, db: DbDep, llm) -> dict | None:
    """Run the relevant bot based on intent."""
    # Try to extract startup name from message
    # This is a simplified version - in production, use NER
    
    # For demo purposes, just return mock data
    # In production, extract startup ID and run actual bot
    return None


def format_bot_results(bot_results: dict | None) -> str:
    """Format bot results for the prompt."""
    if not bot_results:
        return ""
    return f"\nBot analysis results:\n{str(bot_results)}\n"


def generate_suggested_actions(intent: str, context: ConversationContext) -> list[dict]:
    """Generate suggested actions based on intent."""
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
    """Generate related insights based on intent."""
    insights = []
    
    # Get some startups for demo purposes
    try:
        result = await db.execute(select(Startup).limit(3))
        startups = result.scalars().all()
        
        for startup in startups:
            insights.append({
                "type": "startup",
                "title": startup.name,
                "description": f"{startup.industry or 'Tech'} startup at {startup.stage or 'early'} stage",
                "relevance_score": 0.85,
            })
    except Exception:
        pass
    
    return insights


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(conversation_id: str) -> list[ChatMessage]:
    """Get conversation history."""
    if conversation_id not in _conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    return _conversations[conversation_id].history


@router.post("/conversations/{conversation_id}/clear")
async def clear_conversation(conversation_id: str) -> dict:
    """Clear conversation history."""
    if conversation_id in _conversations:
        _conversations[conversation_id].history.clear()
        return {"message": "Conversation cleared", "conversation_id": conversation_id}
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Conversation not found"
    )


@router.get("/intents")
async def get_available_intents() -> dict:
    """Get list of available intents and their descriptions."""
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
