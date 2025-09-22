# app/schemas.py
from __future__ import annotations

from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ---- Meetings ----

class MeetingCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    department: Optional[str] = Field(None, max_length=128)
    country: Optional[str] = Field(None, max_length=64)
    deadline_at: Optional[datetime] = None


class MeetingOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    country: Optional[str] = None
    deadline_at: Optional[datetime] = None
    status: Literal["draft", "open", "closed"]
    created_by: Optional[int] = None
    created_at: datetime


# ---- Questions ----

QuestionType = Literal["text", "choice", "multi", "bool", "int"]

class QuestionCreate(BaseModel):
    meeting_id: int
    text: str = Field(..., min_length=1)
    order_idx: int = 0
    is_required: bool = True
    type: QuestionType = "text"
    options: Optional[List[str]] = None

    @field_validator("options")
    @classmethod
    def _strip_options(cls, v):
        if v:
            v = [s.strip() for s in v if s and s.strip()]
            if not v:
                return None
        return v


class QuestionOut(BaseModel):
    id: int
    meeting_id: int
    text: str
    order_idx: int
    is_required: bool
    type: QuestionType
    options: List[str] = []  # плоский список значений (value/label одинаковые в базе)


# ---- Responses / Answers ----

class AnswerOut(BaseModel):
    question_id: int
    value: str


class ResponseOut(BaseModel):
    id: int
    user_id: int
    meeting_id: int
    status: Literal["draft", "submitted"]
    submitted_at: Optional[datetime] = None
    answers: List[AnswerOut] = []
