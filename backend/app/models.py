from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReadingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    value: float = Field(gt=0, allow_inf_nan=False)
    memo: str = Field(default="", max_length=500)

    @field_validator("date", mode="before")
    @classmethod
    def require_yyyy_mm_dd(cls, value):
        if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
        return value

    @field_validator("value", mode="before")
    @classmethod
    def require_number(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("독서 시간은 숫자로 입력해야 합니다.")
        return value


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
