# app/models.py
from __future__ import annotations

import enum
from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    Text,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


# ---------- Enums ----------

class MeetingStatus(enum.Enum):
    draft = "draft"
    open = "open"
    closed = "closed"
    scheduled = "scheduled"



class QuestionType(enum.Enum):
    text = "text"
    choice = "choice"
    multi = "multi"
    bool = "bool"
    int = "int"


# ---------- Tables ----------

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)  # NEW
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)      # NEW
    telegram_id: Mapped[int | None] = mapped_column(nullable=True, index=True)         # теперь nullable
    fio: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    role: Mapped["Role"] = relationship()


class TgSession(Base):
    __tablename__ = "tg_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(Enum(MeetingStatus), default=MeetingStatus.draft)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="Question.order_idx"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text())
    order_idx: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), default=QuestionType.text)

    meeting: Mapped["Meeting"] = relationship(back_populates="questions")
    options: Mapped[list["Option"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    value: Mapped[str] = mapped_column(String(128))
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)

    question: Mapped["Question"] = relationship(back_populates="options")


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | submitted


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    response_id: Mapped[int] = mapped_column(ForeignKey("responses.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    value: Mapped[str] = mapped_column(Text())
