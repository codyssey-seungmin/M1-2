from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    value: float = Field(gt=0, allow_inf_nan=False)
    memo: str = Field(default="", max_length=500)


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ConversationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    messages: list[Message] = Field(min_length=1, max_length=50)


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None
