from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(
        ..., description="Identifier of the founder/user", min_length=1
    )
    conversation_id: str = Field(
        ..., description="Identifier of the conversation session", min_length=1
    )
    message: str = Field(
        ..., description="User input message string", min_length=1
    )


class ChatResponse(BaseModel):
    user_id: str
    conversation_id: str
    response: str
