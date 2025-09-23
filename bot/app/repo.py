# app/repo.py
from __future__ import annotations

from typing import Optional, Sequence
from datetime import datetime
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import bcrypt

from .models import (
    User,
    Meeting,
    Question,
    Option,
    Response,
    Answer,
    MeetingStatus,
    QuestionType,
    Role,
    TgSession,
)

# -------- users (старое, по telegram_id) --------

async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    fio: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    res = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = res.scalar_one_or_none()
    if user is None:
        user = User(telegram_id=telegram_id, fio=fio, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


# -------- users (новое: username/password) --------

async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    role_id: int,
    fio: Optional[str] = None,
    email: Optional[str] = None,
) -> User:
    u = User(
        username=username,
        password_hash=bcrypt.hash(password),
        role_id=role_id,
        fio=fio,
        email=email,
        is_active=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    res = await db.execute(select(User).where(User.username == username, User.is_active == True))
    u = res.scalar_one_or_none()
    if not u or not u.password_hash or not bcrypt.verify(password, u.password_hash):
        return None
    return u


# -------- sessions --------

async def set_active_session(db: AsyncSession, telegram_id: int, user_id: int) -> TgSession:
    await db.execute(
        update(TgSession).where(
            TgSession.telegram_id == telegram_id, TgSession.is_active == True
        ).values(is_active=False)
    )
    s = TgSession(telegram_id=telegram_id, user_id=user_id, is_active=True)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def get_active_user(db: AsyncSession, telegram_id: int) -> User | None:
    q = (
        select(User)
        .join(TgSession, TgSession.user_id == User.id)
        .where(TgSession.telegram_id == telegram_id, TgSession.is_active == True)
        .order_by(TgSession.id.desc())
    )
    return (await db.execute(q)).scalars().first()


async def logout(db: AsyncSession, telegram_id: int) -> None:
    await db.execute(
        update(TgSession).where(
            TgSession.telegram_id == telegram_id, TgSession.is_active == True
        ).values(is_active=False)
    )
    await db.commit()


# -------- roles CRUD --------

async def list_roles(db: AsyncSession):
    return (await db.execute(select(Role).order_by(Role.id))).scalars().all()


async def create_role(db: AsyncSession, name: str) -> Role:
    r = Role(name=name)
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def rename_role(db: AsyncSession, role_id: int, new_name: str) -> None:
    await db.execute(update(Role).where(Role.id == role_id).values(name=new_name))
    await db.commit()


async def delete_role(db: AsyncSession, role_id: int) -> bool:
    used = (await db.execute(select(User).where(User.role_id == role_id))).scalars().first()
    if used:
        return False
    await db.execute(delete(Role).where(Role.id == role_id))
    await db.commit()
    return True


async def set_user_role(db: AsyncSession, username: str, role_id: int) -> bool:
    res = await db.execute(select(User).where(User.username == username))
    u = res.scalar_one_or_none()
    if not u:
        return False
    u.role_id = role_id
    await db.commit()
    return True


# -------- meetings --------

async def create_meeting(
    db: AsyncSession,
    created_by: int,
    title: str,
    description: Optional[str],
    department: Optional[str],
    country: Optional[str],
    deadline_at: Optional[datetime],
) -> Meeting:
    m = Meeting(
        title=title,
        description=description,
        department=department,
        country=country,
        deadline_at=deadline_at,
        status=MeetingStatus.draft,
        created_by=created_by,
    )
    db.add(m)
    await db.commit()
    await db.refresh(m)
    return m


async def set_meeting_status(
    db: AsyncSession,
    meeting_id: int,
    status: MeetingStatus,
) -> None:
    await db.execute(
        update(Meeting).where(Meeting.id == meeting_id).values(status=status)
    )
    await db.commit()


async def list_open_meetings(db: AsyncSession) -> Sequence[Meeting]:
    res = await db.execute(
        select(Meeting)
        .where(Meeting.status == MeetingStatus.open)
        .order_by(Meeting.id.desc())
    )
    return res.scalars().all()


async def get_meeting(db: AsyncSession, meeting_id: int) -> Optional[Meeting]:
    res = await db.execute(
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(
            selectinload(Meeting.questions).options(
                selectinload(Question.options)
            )
        )
    )
    m = res.unique().scalar_one_or_none()
    if m and m.questions:
        m.questions.sort(key=lambda q: (q.order_idx, q.id))
    return m


# -------- questions --------

async def add_question(
    db: AsyncSession,
    meeting_id: int,
    text: str,
    qtype: str,
    order_idx: int,
    is_required: bool,
    options: Optional[list[str]] = None,
) -> Question:
    q = Question(
        meeting_id=meeting_id,
        text=text,
        order_idx=order_idx,
        is_required=is_required,
        type=QuestionType(qtype),
    )
    db.add(q)
    await db.flush()

    if options:
        for opt in options:
            val = opt.strip()
            if val:
                db.add(Option(question_id=q.id, value=val, label=val))

    await db.commit()
    await db.refresh(q)
    return q


# -------- responses / answers --------

async def get_or_create_response(
    db: AsyncSession,
    user_id: int,
    meeting_id: int,
) -> Response:
    res = await db.execute(
        select(Response).where(
            Response.user_id == user_id,
            Response.meeting_id == meeting_id,
        )
    )
    r = res.scalar_one_or_none()
    if r is None:
        r = Response(user_id=user_id, meeting_id=meeting_id, status="draft")
        db.add(r)
        await db.commit()
        await db.refresh(r)
    return r


async def save_answer(
    db: AsyncSession,
    response_id: int,
    question_id: int,
    value: str,
) -> Answer:
    ans = Answer(response_id=response_id, question_id=question_id, value=value)
    db.add(ans)
    await db.commit()
    return ans


async def submit_response(db: AsyncSession, response_id: int) -> None:
    res = await db.execute(select(Response).where(Response.id == response_id))
    r = res.scalar_one_or_none()
    if r:
        r.status = "submitted"
        r.submitted_at = datetime.utcnow()
        await db.commit()
