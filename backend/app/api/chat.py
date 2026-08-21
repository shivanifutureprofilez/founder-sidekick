from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.agent.sidekick_agent import run_agent_turn

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to Founder Sidekick AI Agent",
    description="Processes user message, executes Agno AI Agent turn, and returns agent response.",
)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    POST /chat endpoint handler.
    Delegates to run_agent_turn to process context, run agent, and persist history.
    """
    try:
        response_text = run_agent_turn(
            db=db,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            message=request.message,
        )
        return ChatResponse(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            response=response_text,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing chat turn: {str(e)}",
        )
