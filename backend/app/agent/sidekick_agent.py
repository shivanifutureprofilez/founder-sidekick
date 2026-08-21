import os
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from agno.agent import Agent
from agno.models.google import Gemini

from app.services.user_service import UserService
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.context.context_manager import ContextManager
from app.tools.idea_tools import save_idea, get_idea, list_ideas


SYSTEM_INSTRUCTIONS = """You are Founder Sidekick, an intelligent AI companion for startup founders.

Your goals:
1. Support the founder in managing ideas, making strategic decisions, and thinking through product/business problems.
2. Use persistent tools when asked to save, list, or retrieve startup ideas.
3. Utilize durable long-term memories provided in your context to give personalized, coherent answers across sessions.
4. Understand and reference recent conversation history accurately.

Tool Usage Rules:
- When a user wants to record or save an idea, call `save_idea(title, description)`.
- When a user asks for saved ideas or lists of ideas, call `list_ideas()`.
- When a user asks about a specific saved idea by title or ID, call `get_idea(identifier)`.
- Only call tools when an action requires persistent storage or lookup.
- Be concise, helpful, direct, and pragmatic.
"""


def create_sidekick_agent(db: Session, user_id: str) -> Agent:
    """
    Configures and returns an Agno Agent instance using Google Gemini Flash.
    Registers persistent idea tools bound to the current DB session and user_id.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")
    model_id = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Define user/session-bound tool wrappers with clean agent-facing signatures
    def bound_save_idea(title: str, description: str) -> Dict[str, Any]:
        """Saves a new startup idea persistently for the founder.

        Args:
            title: The title or headline of the idea.
            description: Detailed description of the idea.
        """
        return save_idea(db, user_id=user_id, title=title, description=description)

    def bound_get_idea(identifier: str) -> Dict[str, Any]:
        """Retrieves a saved startup idea by title or UUID string.

        Args:
            identifier: Title or UUID string of the idea to look up.
        """
        return get_idea(db, user_id=user_id, identifier=identifier)

    def bound_list_ideas() -> Dict[str, Any]:
        """Lists all persistent startup ideas saved for the founder."""
        return list_ideas(db, user_id=user_id)

    # Initialize Gemini model
    model = Gemini(id=model_id, api_key=api_key if api_key else None)

    # Create Agno Agent
    agent = Agent(
        model=model,
        tools=[bound_save_idea, bound_get_idea, bound_list_ideas],
        instructions=SYSTEM_INSTRUCTIONS,
        markdown=True,
    )
    return agent


def _format_context_prompt(context: Dict[str, Any], user_message: str) -> str:
    """Formats system context payload into a prompt string for LLM execution."""
    prompt_parts: List[str] = []

    # Include Durable Memories if present
    memories = context.get("memories", [])
    if memories:
        prompt_parts.append("### Durable Founder Memories:")
        for mem in memories:
            prompt_parts.append(
                f"- [{mem.type.upper()}] {mem.key}: {mem.value} (Importance: {mem.importance})"
            )
        prompt_parts.append("")

    # Include Conversation Summary if present
    summary = context.get("summary")
    if summary:
        prompt_parts.append(f"### Previous Conversation Summary:\n{summary}\n")

    # Include Recent Bounded Message History
    recent_messages = context.get("recent_messages", [])
    if recent_messages:
        prompt_parts.append("### Recent Conversation History:")
        for msg in recent_messages:
            prompt_parts.append(f"{msg.role.capitalize()}: {msg.content}")
        prompt_parts.append("")

    # Include Current Turn Input
    prompt_parts.append(f"Founder: {user_message}")

    return "\n".join(prompt_parts)


def run_agent_turn(
    db: Session, user_id: str, conversation_id: str, message: str
) -> str:
    """
    Orchestrates a complete chat turn:
    1. Ensures user and conversation exist.
    2. Builds bounded prompt context via ContextManager.
    3. Persists incoming user message turn.
    4. Executes the Agno agent.
    5. Persists assistant response turn.
    6. Returns assistant response string.
    """
    # 1 & 2. Ensure entities exist
    UserService.get_or_create_user(db, user_id)
    ConversationService.get_or_create_conversation(
        db, user_id=user_id, conversation_id=conversation_id
    )

    # 3. Build bounded context payload
    context = ContextManager.build_context(
        db, user_id=user_id, conversation_id=conversation_id
    )

    # 4. Save user message to PostgreSQL
    MessageService.create_message(
        db, conversation_id=conversation_id, role="user", content=message
    )

    # 5. Format prompt and run Agno Agent
    prompt = _format_context_prompt(context, message)
    agent = create_sidekick_agent(db, user_id)

    response = agent.run(prompt)
    response_text = (
        response.content
        if hasattr(response, "content") and response.content
        else str(response)
    )

    # 6. Save assistant message response to PostgreSQL
    MessageService.create_message(
        db, conversation_id=conversation_id, role="assistant", content=response_text
    )

    return response_text
